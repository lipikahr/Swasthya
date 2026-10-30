"""Single calorie-goal rule used by charts, celebrations, and meal suggestions.

A day with no saved meals is `no_data`, not a miss. Intake within
GOAL_CALORIE_TOLERANCE of the active calorie target is `met`. Below that band
is `below`. Above that band is `above`. The language model does not decide this.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings

from apps.targets.services import current_target

from .models import DailyGoalAchievement
from .services import get_daily_progress

GOAL_MET = "met"
GOAL_BELOW = "below"
GOAL_ABOVE = "above"
GOAL_NO_DATA = "no_data"
GOAL_NO_TARGET = "no_target"

LABELS = {
    GOAL_MET: "Goal met",
    GOAL_BELOW: "Below target",
    GOAL_ABOVE: "Above target",
    GOAL_NO_DATA: "No data",
    GOAL_NO_TARGET: "No target",
}


def calorie_tolerance() -> Decimal:
    return Decimal(str(getattr(settings, "GOAL_CALORIE_TOLERANCE", "0.05")))


def status_from_progress(progress: dict, target_calories) -> str:
    if progress.get("meal_count", 0) == 0:
        return GOAL_NO_DATA
    if target_calories is None:
        return GOAL_NO_TARGET
    eaten = progress["consumed"].get("energy_kcal")
    if eaten is None:
        return GOAL_NO_DATA
    goal = Decimal(str(target_calories))
    if goal <= 0:
        return GOAL_NO_TARGET
    ratio = (Decimal(str(eaten)) - goal) / goal
    band = calorie_tolerance()
    if abs(ratio) <= band:
        return GOAL_MET
    if ratio < 0:
        return GOAL_BELOW
    return GOAL_ABOVE


def day_goal_status(user, on_date: date | None = None) -> dict:
    progress = get_daily_progress(user, on_date)
    target = current_target(user)
    calories = None if target is None else target.calories
    status = status_from_progress(progress, calories)
    return {
        **progress,
        "goal_status": status,
        "goal_label": LABELS[status],
        "target_calories": None if calories is None else calories,
        "tolerance": str(calorie_tolerance()),
    }


def range_goal_status(user, start: date, end: date) -> list[dict]:
    days = []
    cursor = start
    while cursor <= end:
        days.append({**day_goal_status(user, cursor), "date": cursor.isoformat()})
        cursor += timedelta(days=1)
    return days


def record_new_achievement(*, user, day: date, before: str, after: str, meal) -> dict | None:
    if after != GOAL_MET or before == GOAL_MET:
        if after != GOAL_MET:
            DailyGoalAchievement.objects.filter(user=user, day=day).delete()
        return None
    _, created = DailyGoalAchievement.objects.get_or_create(user=user, day=day, defaults={"meal": meal})
    if not created:
        return None
    return {
        "show": True,
        "title": "Daily goal reached!",
        "message": "Great progress. You've met today's nutrition target.",
        "date": day.isoformat(),
    }


def sync_achievement_for_day(user, day: date) -> None:
    if day_goal_status(user, day)["goal_status"] != GOAL_MET:
        DailyGoalAchievement.objects.filter(user=user, day=day).delete()
