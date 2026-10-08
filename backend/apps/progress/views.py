from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.targets.serializers import TargetSerializer
from apps.targets.services import current_target

from .services import get_daily_progress, get_streaks


def _day(request):
    raw = request.query_params.get("date")
    if not raw:
        return timezone.now().date()
    parsed = parse_date(raw)
    if parsed is None:
        raise ValidationError({"date": ["Use YYYY-MM-DD."]})
    return parsed


class DailyProgressView(APIView):
    def get(self, request):
        progress = get_daily_progress(request.user, _day(request))
        return Response(_json_ready(progress))


class StreakView(APIView):
    def get(self, request):
        return Response(get_streaks(request.user, timezone.now().date()))


class DashboardView(APIView):
    def get(self, request):
        day = timezone.now().date()
        progress = get_daily_progress(request.user, day)
        target = current_target(request.user)
        return Response(
            {
                "date": day.isoformat(),
                "progress": _json_ready(progress),
                "target": None if target is None else TargetSerializer(target).data,
                "streaks": get_streaks(request.user, day),
            }
        )


def _json_ready(progress: dict) -> dict:
    consumed = {name: None if value is None else str(value) for name, value in progress["consumed"].items()}
    remaining = progress["remaining"]
    if remaining is not None:
        remaining = {name: None if value is None else str(value) for name, value in remaining.items()}
    return {**progress, "consumed": consumed, "remaining": remaining}
