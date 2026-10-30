from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView, TokenRefreshView

from .password_reset import confirm_reset, request_reset
from .password_serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetTokenSerializer,
)
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=201,
        )


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    authentication_classes = []


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []


class LogoutView(TokenBlacklistView):
    permission_classes = [AllowAny]
    authentication_classes = []


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = request_reset(serializer.validated_data["email"])
        return Response({"message": message})


class PasswordResetValidateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"valid": True})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = confirm_reset(
            serializer.validated_data["uid"],
            serializer.validated_data["token"],
            serializer.validated_data["password"],
        )
        return Response({"message": message})
