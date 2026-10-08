"""Throwaway routes that exist only so tests can exercise shared behaviour
(auth requirement, error shape) before the real endpoints are built."""
from django.urls import include, path
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class ProtectedView(APIView):
    def get(self, request):
        return Response({"email": request.user.email})


class Payload(serializers.Serializer):
    age = serializers.IntegerField(min_value=1)


class ValidatedView(APIView):
    def post(self, request):
        Payload(data=request.data).is_valid(raise_exception=True)
        return Response({"ok": True})


urlpatterns = [
    path("protected/", ProtectedView.as_view()),
    path("validated/", ValidatedView.as_view()),
    path("", include("config.urls")),
]
