from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.conversations.models import Conversation, MealDraft
from apps.nutrition.allergens import suggestion_allowed
from apps.nutrition.calculation import NutritionError, calculate_nutrition, calculate_user_food
from apps.nutrition.models import Food, UserFood
from apps.progress.services import get_remaining_targets
from apps.profiles.models import UserProfile
from apps.targets.services import current_target

from .models import DayPlan, PlannedSlot

SLOTS = (
    PlannedSlot.Slot.BREAKFAST,
    PlannedSlot.Slot.LUNCH,
    PlannedSlot.Slot.SNACK,
    PlannedSlot.Slot.DINNER,
)
SLOT_SHARE = {
    PlannedSlot.Slot.BREAKFAST: Decimal("0.25"),
    PlannedSlot.Slot.LUNCH: Decimal("0.35"),
    PlannedSlot.Slot.SNACK: Decimal("0.15"),
    PlannedSlot.Slot.DINNER: Decimal("0.25"),
}


def get_or_none_plan(user, on_date: date) -> DayPlan | None:
    return DayPlan.objects.filter(user=user, date=on_date).prefetch_related("slots__food", "slots__user_food").first()


def serialize_plan(plan: DayPlan | None, *, limitation: str | None = None) -> dict:
    if plan is None:
        return {"date": None, "slots": [], "limitation": limitation}
    slots = []
    for slot in plan.slots.all():
        food_name = slot.user_food.name if slot.user_food_id else slot.food.food_name
        slots.append(
            {
                "id": slot.id,
                "slot": slot.slot,
                "food_code": slot.food.food_code if slot.food_id else "",
                "user_food_id": slot.user_food_id,
                "food_name": food_name,
                "quantity": str(slot.quantity),
                "unit": slot.unit,
                "nutrition_snapshot": slot.nutrition_snapshot,
                "status": slot.status,
                "logged_meal_id": slot.logged_meal_id,
                "provenance": "user_provided" if slot.user_food_id else "verified",
            }
        )
    return {"id": plan.id, "date": plan.date.isoformat(), "slots": slots, "limitation": limitation}


def generate_day_plan(user, on_date: date | None = None, *, include_user_foods: bool = True) -> dict:
    day = on_date or timezone.now().date()
    target = current_target(user)
    if target is None:
        raise ValidationError("Set a daily target before generating a plan.")
    remaining = get_remaining_targets(user, on_date=day) or {}
    calorie_budget = remaining.get("calories")
    if calorie_budget is None:
        calorie_budget = target.calories
    calorie_budget = Decimal(str(calorie_budget))
    if calorie_budget <= 0:
        raise ValidationError("Today's calorie target is already met or exceeded, so a plan was not generated.")
    profile = UserProfile.objects.filter(user=user).first()
    candidates = _candidates(user, profile, include_user_foods=include_user_foods)
    if not candidates:
        return serialize_plan(get_or_none_plan(user, day), limitation="No eligible foods match your remaining targets and diet filters.")
    assigned = _assign_slots(candidates, calorie_budget)
    if not assigned:
        return serialize_plan(get_or_none_plan(user, day), limitation="No eligible foods match your remaining targets and diet filters.")
    with transaction.atomic():
        plan, _ = DayPlan.objects.get_or_create(user=user, date=day)
        plan.slots.all().delete()
        for slot_name, pick in assigned.items():
            PlannedSlot.objects.create(
                plan=plan,
                slot=slot_name,
                food=pick.get("food"),
                user_food=pick.get("user_food"),
                quantity=pick["quantity"],
                unit=pick["unit"],
                nutrition_snapshot=pick["snapshot"],
                status=PlannedSlot.Status.PLANNED,
            )
        plan.save(update_fields=["updated_at"])
    return serialize_plan(get_or_none_plan(user, day))


def swap_slot(user, slot: PlannedSlot) -> dict:
    profile = UserProfile.objects.filter(user=user).first()
    current_code = slot.food.food_code if slot.food_id else None
    current_user = slot.user_food_id
    candidates = [
        item
        for item in _candidates(user, profile, include_user_foods=True)
        if item.get("food_code") != current_code and item.get("user_food_id") != current_user
    ]
    alternatives = candidates[:5]
    return {
        "slot_id": slot.id,
        "alternatives": [
            {
                "food_code": item.get("food_code") or "",
                "user_food_id": item.get("user_food_id"),
                "food_name": item["food_name"],
                "quantity": str(item["quantity"]),
                "unit": item["unit"],
                "provenance": item["provenance"],
                "nutrition_snapshot": item["snapshot"],
            }
            for item in alternatives
        ],
        "limitation": None if alternatives else "No other eligible foods were found for this slot.",
    }


def accept_swap(user, slot: PlannedSlot, *, food_code: str = "", user_food_id: int | None = None) -> PlannedSlot:
    profile = UserProfile.objects.filter(user=user).first()
    pick = None
    for item in _candidates(user, profile, include_user_foods=True):
        if food_code and item.get("food_code") == food_code:
            pick = item
            break
        if user_food_id and item.get("user_food_id") == user_food_id:
            pick = item
            break
    if pick is None:
        raise ValidationError("That alternative is not eligible for your diet filters.")
    slot.food = pick.get("food")
    slot.user_food = pick.get("user_food")
    slot.quantity = pick["quantity"]
    slot.unit = pick["unit"]
    slot.nutrition_snapshot = pick["snapshot"]
    slot.status = PlannedSlot.Status.SWAPPED
    slot.logged_meal = None
    slot.save()
    return slot


def seed_log_this(user, slot: PlannedSlot) -> dict:
    from apps.agent.workflow import build_confirmation

    conversation = Conversation.objects.create(user=user)
    items = [
        {
            "food_query": slot.user_food.name if slot.user_food_id else slot.food.food_name,
            "food_code": slot.food.food_code if slot.food_id else "",
            "user_food_id": slot.user_food_id,
            "food_name": slot.user_food.name if slot.user_food_id else slot.food.food_name,
            "quantity": str(slot.quantity),
            "unit": slot.unit,
            "quantity_confirmed": True,
            "status": "ready",
            "candidates": [],
        }
    ]
    MealDraft.objects.update_or_create(
        conversation=conversation,
        defaults={"user": user, "meal_type": slot.slot, "status": "awaiting_confirmation", "items": items},
    )
    return {
        "conversation_id": conversation.id,
        "confirmation": build_confirmation(slot.slot, items),
        "slot_id": slot.id,
    }


def mark_slot_logged(user, meal) -> None:
    plan = DayPlan.objects.filter(user=user, date=meal.timestamp.date()).first()
    if plan is None:
        return
    slot = plan.slots.filter(slot=meal.meal_type, status__in=[PlannedSlot.Status.PLANNED, PlannedSlot.Status.SWAPPED]).first()
    if slot is None:
        return
    slot.status = PlannedSlot.Status.LOGGED
    slot.logged_meal = meal
    slot.save(update_fields=["status", "logged_meal"])


def _candidates(user, profile, *, include_user_foods: bool) -> list[dict]:
    rows = []
    for food in Food.objects.all().order_by("food_name")[:600]:
        allowed, reason = suggestion_allowed(name=food.food_name, ingredients="", profile=profile)
        if not allowed:
            continue
        try:
            result = calculate_nutrition(food.food_code, Decimal("100"), "g")
        except NutritionError:
            continue
        energy = result["nutrients"].get("energy_kcal")
        if energy is None:
            continue
        rows.append(
            {
                "food": food,
                "user_food": None,
                "food_code": food.food_code,
                "user_food_id": None,
                "food_name": food.food_name,
                "quantity": Decimal("100"),
                "unit": "g",
                "energy": Decimal(str(energy)),
                "provenance": "verified",
                "snapshot": {name: None if value is None else str(value) for name, value in result["nutrients"].items()},
                "reason": reason,
            }
        )
    if include_user_foods:
        for user_food in UserFood.objects.filter(user=user):
            allowed, reason = suggestion_allowed(
                name=user_food.name,
                ingredients=user_food.ingredients,
                profile=profile,
                require_ingredients=True,
            )
            if not allowed:
                continue
            try:
                result = calculate_user_food(user_food, user_food.serving_amount, user_food.serving_unit)
            except NutritionError:
                continue
            energy = result["nutrients"].get("energy_kcal")
            if energy is None:
                continue
            rows.append(
                {
                    "food": None,
                    "user_food": user_food,
                    "food_code": None,
                    "user_food_id": user_food.id,
                    "food_name": user_food.name,
                    "quantity": user_food.serving_amount,
                    "unit": user_food.serving_unit,
                    "energy": Decimal(str(energy)),
                    "provenance": "user_provided",
                    "snapshot": {name: None if value is None else str(value) for name, value in result["nutrients"].items()},
                    "reason": reason,
                }
            )
    rows.sort(key=lambda item: item["energy"])
    return rows


def _assign_slots(candidates: list[dict], calorie_budget: Decimal) -> dict:
    assigned = {}
    used = set()
    remaining = calorie_budget
    for slot in SLOTS:
        share = remaining * SLOT_SHARE[slot] if remaining > 0 else Decimal("0")
        pick = None
        best = None
        for index, item in enumerate(candidates):
            key = ("c", item.get("food_code")) if item.get("food_code") else ("u", item.get("user_food_id"))
            if key in used:
                continue
            if item["energy"] <= share + Decimal("40"):
                distance = abs(item["energy"] - share)
                if best is None or distance < best[0]:
                    best = (distance, index, item, key)
        if best is None:
            for index, item in enumerate(candidates):
                key = ("c", item.get("food_code")) if item.get("food_code") else ("u", item.get("user_food_id"))
                if key in used:
                    continue
                pick = item
                used.add(key)
                break
        else:
            pick = best[2]
            used.add(best[3])
        if pick is None:
            continue
        assigned[slot] = pick
        remaining -= pick["energy"]
    return assigned
