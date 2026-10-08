from rest_framework.response import Response
from rest_framework.views import APIView

from .models import NutritionTarget
from .serializers import CustomizeSerializer, TargetSerializer
from .services import accept_suggestion, current_target, customize_target, suggestion_for


class TargetCurrentView(APIView):
    def get(self, request):
        target = current_target(request.user)
        return Response({"target": None if target is None else TargetSerializer(target).data})


class TargetHistoryView(APIView):
    def get(self, request):
        history = NutritionTarget.objects.filter(user=request.user)
        return Response({"results": TargetSerializer(history, many=True).data})


class SuggestTargetView(APIView):
    def post(self, request):
        numbers = suggestion_for(request.user)
        current = current_target(request.user)
        return Response(
            {
                "suggestion": numbers,
                "saved": False,
                "current_source": None if current is None else current.source,
            }
        )


class AcceptSuggestionView(APIView):
    def post(self, request):
        target = accept_suggestion(request.user)
        return Response(TargetSerializer(target).data, status=201)


class CustomizeTargetView(APIView):
    def post(self, request):
        serializer = CustomizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = customize_target(request.user, serializer.validated_data)
        return Response(TargetSerializer(target).data, status=201)
