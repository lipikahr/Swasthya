from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.targets.serializers import TargetSerializer
from apps.targets.services import current_target, weekly_budget

from .goal import day_goal_status, range_goal_status
from .services import get_streaks, most_logged_foods, weekly_consumed


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
        return Response(_json_ready(day_goal_status(request.user, _day(request))))


class RangeProgressView(APIView):
    def get(self, request):
        start = parse_date(request.query_params.get("start") or "")
        end = parse_date(request.query_params.get("end") or "")
        if start is None or end is None or end < start:
            raise ValidationError({"date": ["Use start and end as YYYY-MM-DD."]})
        if (end - start).days > 40:
            raise ValidationError({"date": ["Choose a range of 40 days or fewer."]})
        days = [_json_ready(row) for row in range_goal_status(request.user, start, end)]
        summary = {
            "met": sum(1 for row in days if row["goal_status"] == "met"),
            "below": sum(1 for row in days if row["goal_status"] == "below"),
            "above": sum(1 for row in days if row["goal_status"] == "above"),
            "no_data": sum(1 for row in days if row["goal_status"] == "no_data"),
            "no_target": sum(1 for row in days if row["goal_status"] == "no_target"),
        }
        return Response({"start": start.isoformat(), "end": end.isoformat(), "days": days, "summary": summary})


class StreakView(APIView):
    def get(self, request):
        return Response(get_streaks(request.user, timezone.now().date()))


class DashboardView(APIView):
    def get(self, request):
        day = _day(request)
        progress = day_goal_status(request.user, day)
        target = current_target(request.user)
        week_start = day - timedelta(days=day.weekday())
        week_end = week_start + timedelta(days=6)
        week_eaten = weekly_consumed(request.user, week_start, week_end)
        week_goal = weekly_budget(target)
        weekly = None
        if week_goal is not None:
            weekly = {
                "start": week_start.isoformat(),
                "end": week_end.isoformat(),
                "consumed_calories": None if week_eaten.get("energy_kcal") is None else str(week_eaten["energy_kcal"]),
                "target_calories": str(week_goal["calories"]),
                "derived_from_daily": week_goal["derived_from_daily"],
            }
        return Response(
            {
                "date": day.isoformat(),
                "progress": _json_ready(progress),
                "target": None if target is None else TargetSerializer(target).data,
                "streaks": get_streaks(request.user, day),
                "weekly": weekly,
                "most_logged_foods": most_logged_foods(request.user),
            }
        )


def _json_ready(progress: dict) -> dict:
    consumed = {name: None if value is None else str(value) for name, value in progress["consumed"].items()}
    remaining = progress["remaining"]
    if remaining is not None:
        remaining = {name: None if value is None else str(value) for name, value in remaining.items()}
    ready = {**progress, "consumed": consumed, "remaining": remaining}
    if ready.get("target_calories") is not None:
        ready["target_calories"] = str(ready["target_calories"])
    return ready
