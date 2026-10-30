from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agent.providers import gemini_configuration
from apps.agent.speech import sarvam_configuration


class HealthGeminiSerializer(serializers.Serializer):
    key_configured = serializers.BooleanField()
    provider = serializers.CharField()
    model = serializers.CharField()


class HealthOkSerializer(serializers.Serializer):
    status = serializers.CharField()
    database = serializers.BooleanField()
    gemini = HealthGeminiSerializer()


class HealthView(APIView):
    """Reports whether the API is up and can reach the database."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        responses={
            200: HealthOkSerializer,
            503: OpenApiResponse(description="API is up but the database is unreachable."),
        },
        auth=[],
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_ok = True
        except Exception:  # health check must never raise
            db_ok = False
        return Response(
            {
                "status": "ok" if db_ok else "degraded",
                "database": db_ok,
                "gemini": gemini_configuration(),
                "sarvam": sarvam_configuration(),
            },
            status=200 if db_ok else 503,
        )
