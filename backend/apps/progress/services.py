"""Daily totals and streaks are derived from saved meals. They are not a second record of what was eaten."""

from datetime import date
from decimal import Decimal

from django.utils import timezone

from apps.meals.models import MealItem
from apps.nutrition.nutrients import NUTRIENT_FIELDS
from apps.targets.services import current_target

TARGET_FIELDS = ("calories", "protein_g", "carbohydrates_g", "fat_g", "fibre_g")
SNAPSHOT_FOR_TARGET = {
    "calories": "energy_kcal",
    "protein_g": "protein_g",
    "carbohydrates_g": "carb_g",
    "fat_g": "fat_g",
    "fibre_g": "fibre_g",
}


def get_daily_progress(user, on_date: date | None = None) -> dict:
    day = on_date or timezone.now().date()
    items = MealItem.objects.filter(meal__user=user, meal__timestamp__date=day)
    consumed = {name: Decimal("0") for name in NUTRIENT_FIELDS}
    missing = set()
    meal_ids = set()
    for item in items.select_related("meal"):
        meal_ids.add(item.meal_id)
        snapshot = item.nutrition_snapshot or {}
        for name in NUTRIENT_FIELDS:
            raw = snapshot.get(name)
            if raw is None:
                missing.add(name)
            elif name not in missing:
                consumed[name] += Decimal(str(raw))
    if not items:
        consumed = {name: Decimal("0") for name in NUTRIENT_FIELDS}
    else:
        for name in missing:
            consumed[name] = None
    return {
        "date": day.isoformat(),
        "meal_count": len(meal_ids),
        "consumed": consumed,
        "remaining": get_remaining_targets(user, consumed),
    }


def get_remaining_targets(user, consumed: dict | None = None, on_date: date | None = None) -> dict | None:
    target = current_target(user)
    if target is None:
        return None
    if consumed is None:
        consumed = get_daily_progress(user, on_date)["consumed"]
    remaining = {}
    for name, snapshot_name in SNAPSHOT_FOR_TARGET.items():
        eaten = consumed.get(snapshot_name)
        goal = getattr(target, name)
        remaining[name] = None if eaten is None else goal - eaten
    return remaining


def get_streaks(user, today: date | None = None) -> dict:
    day = today or timezone.now().date()
    meal_days = set(
        MealItem.objects.filter(meal__user=user).values_list("meal__timestamp__date", flat=True).distinct()
    )
    # values_list date can return datetimes depending on backend; normalize.
    meal_days = {_as_date(value) for value in meal_days}
    return {
        "weekly": _consecutive(meal_days, day, step="week"),
        "monthly": _consecutive(meal_days, day, step="month"),
        "rule": "A day counts when it has at least one saved meal. The current week or month does not break a streak until it ends empty.",
    }


def _consecutive(meal_days: set[date], today: date, step: str) -> int:
    groups = {_bucket(value, step) for value in meal_days}
    cursor = today
    if _bucket(cursor, step) not in groups:
        cursor = _previous(cursor, step)
    streak = 0
    while _bucket(cursor, step) in groups:
        streak += 1
        cursor = _previous(cursor, step)
    return streak


def _bucket(value: date, step: str):
    if step == "week":
        iso = value.isocalendar()
        return iso.year, iso.week
    return value.year, value.month


def _previous(value: date, step: str) -> date:
    if step == "week":
        return date.fromordinal(value.toordinal() - 7)
    year = value.year
    month = value.month - 1
    if month == 0:
        month = 12
        year -= 1
    return date(year, month, 1)


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return value.date()
