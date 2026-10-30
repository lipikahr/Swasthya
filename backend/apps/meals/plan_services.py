from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.conversations.models import Conversation, MealDraft
from apps.nutrition.allergens import suggestion_allowed
from apps.nutrition.calculation import NutritionError, calculate_nutrition, calculate_user_food
from apps.nutrition.food_profile import profile_for
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
SOUTH_HINTS = ("south indian",)
NORTH_HINTS = ("north indian", "punjabi")


def get_or_none_plan(user, on_date: date) -> DayPlan | None:
    return DayPlan.objects.filter(user=user, date=on_date).prefetch_related("slots__food", "slots__user_food").first()


def _preferences(profile: UserProfile | None) -> dict:
    if profile is None:
        return {"diet": "", "cuisines": [], "goal": "", "avoid_sweets": False}
    diet = (profile.diet_pattern or "") or ""
    if not diet and "vegetarian" in (profile.restrictions or []):
        diet = "vegetarian"
    if not diet and "vegan" in (profile.restrictions or []):
        diet = "vegan"
    goal = profile.goal or ""
    return {
        "diet": diet,
        "cuisines": list(profile.preferred_cuisines or []),
        "goal": goal,
        "avoid_sweets": goal in {"lose", "maintain"},
    }


def serialize_plan(plan: DayPlan | None, *, limitation: str | None = None, profile: UserProfile | None = None) -> dict:
    if plan is None:
        return {
            "date": None,
            "slots": [],
            "limitation": limitation,
            "totals": {},
            "target_calories": None,
            "preferences": _preferences(profile),
        }
    slots = []
    totals: dict[str, Decimal] = {}
    for slot in plan.slots.all():
        food_name = slot.user_food.name if slot.user_food_id else slot.food.food_name
        snapshot = slot.nutrition_snapshot or {}
        for key, value in snapshot.items():
            if value in (None, ""):
                continue
            try:
                totals[key] = totals.get(key, Decimal("0")) + Decimal(str(value))
            except Exception:
                continue
        slots.append(
            {
                "id": slot.id,
                "slot": slot.slot,
                "label": slot.label,
                "position": slot.position,
                "source": slot.source,
                "food_code": slot.food.food_code if slot.food_id else "",
                "user_food_id": slot.user_food_id,
                "food_name": food_name,
                "quantity": str(slot.quantity),
                "unit": slot.unit,
                "nutrition_snapshot": snapshot,
                "status": slot.status,
                "logged_meal_id": slot.logged_meal_id,
                "provenance": "user_provided" if slot.user_food_id else "verified",
                "reasons": [],
            }
        )
    target = current_target(plan.user)
    return {
        "id": plan.id,
        "date": plan.date.isoformat(),
        "slots": slots,
        "limitation": limitation,
        "totals": {key: str(value) for key, value in totals.items()},
        "target_calories": None if target is None else str(target.calories),
        "preferences": _preferences(profile or UserProfile.objects.filter(user=plan.user).first()),
    }


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
        return serialize_plan(get_or_none_plan(user, day), limitation="No eligible foods match your remaining targets and diet filters.", profile=profile)
    assigned = _assign_slots(candidates, calorie_budget, profile)
    if not assigned:
        return serialize_plan(get_or_none_plan(user, day), limitation="No eligible foods match your remaining targets and diet filters.", profile=profile)
    with transaction.atomic():
        plan, _ = DayPlan.objects.get_or_create(user=user, date=day)
        plan.slots.filter(source=PlannedSlot.Source.GENERATED, status=PlannedSlot.Status.PLANNED).delete()
        for slot_name, pick in assigned.items():
            position = (plan.slots.filter(slot=slot_name).aggregate(Max("position")).get("position__max") or 0) + 1
            PlannedSlot.objects.create(
                plan=plan,
                slot=slot_name,
                label="",
                position=position,
                source=PlannedSlot.Source.LIKED if pick.get("liked") else PlannedSlot.Source.GENERATED,
                food=pick.get("food"),
                user_food=pick.get("user_food"),
                quantity=pick["quantity"],
                unit=pick["unit"],
                nutrition_snapshot=pick["snapshot"],
                status=PlannedSlot.Status.PLANNED,
            )
        plan.save(update_fields=["updated_at"])
    return serialize_plan(get_or_none_plan(user, day), profile=profile)


def add_slot(user, *, on_date: date, slot: str, food_code: str = "", user_food_id: int | None = None, quantity: str = "1", unit: str = "serving", label: str = "") -> dict:
    if slot not in PlannedSlot.Slot.values:
        raise ValidationError({"slot": ["Choose breakfast, lunch, snack, or dinner."]})
    plan, _ = DayPlan.objects.get_or_create(user=user, date=on_date)
    pick = _resolve_food(user, food_code=food_code, user_food_id=user_food_id, quantity=quantity, unit=unit)
    position = (plan.slots.filter(slot=slot).aggregate(Max("position")).get("position__max") or 0) + 1
    PlannedSlot.objects.create(
        plan=plan,
        slot=slot,
        label=(label or "").strip()[:80],
        position=position,
        source=PlannedSlot.Source.MANUAL,
        food=pick.get("food"),
        user_food=pick.get("user_food"),
        quantity=pick["quantity"],
        unit=pick["unit"],
        nutrition_snapshot=pick["snapshot"],
        status=PlannedSlot.Status.PLANNED,
    )
    profile = UserProfile.objects.filter(user=user).first()
    return serialize_plan(get_or_none_plan(user, on_date), profile=profile)


def remove_slot(user, slot: PlannedSlot) -> dict:
    if slot.status == PlannedSlot.Status.LOGGED:
        raise ValidationError("A logged plan item cannot be removed.")
    day = slot.plan.date
    slot.delete()
    profile = UserProfile.objects.filter(user=user).first()
    return serialize_plan(get_or_none_plan(user, day), profile=profile)


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
        if user_food_id and item.get("user_food_id") == int(user_food_id):
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


def _resolve_food(user, *, food_code: str, user_food_id, quantity: str, unit: str) -> dict:
    if user_food_id:
        user_food = UserFood.objects.filter(user=user, pk=user_food_id).first()
        if user_food is None:
            raise ValidationError({"user_food_id": ["That personal food was not found."]})
        result = calculate_user_food(user_food, quantity or user_food.serving_amount, unit or user_food.serving_unit)
        return {
            "food": None,
            "user_food": user_food,
            "quantity": Decimal(str(quantity or user_food.serving_amount)),
            "unit": unit or user_food.serving_unit,
            "snapshot": {name: None if value is None else str(value) for name, value in result["nutrients"].items()},
        }
    if not food_code:
        raise ValidationError({"food_code": ["Choose a verified food or a personal food."]})
    try:
        result = calculate_nutrition(food_code, Decimal(str(quantity or "1")), unit or "serving")
    except NutritionError:
        try:
            result = calculate_nutrition(food_code, Decimal("100"), "g")
            quantity = "100"
            unit = "g"
        except NutritionError as exc:
            raise ValidationError(str(exc)) from exc
    food = Food.objects.filter(food_code=food_code).first()
    if food is None:
        raise ValidationError({"food_code": ["That food is not in the verified catalogue."]})
    return {
        "food": food,
        "user_food": None,
        "quantity": Decimal(str(quantity or "1")),
        "unit": unit or "serving",
        "snapshot": {name: None if value is None else str(value) for name, value in result["nutrients"].items()},
    }


def _diet_ok(profile_row: dict, profile: UserProfile | None) -> bool:
    diet = (profile.diet_pattern if profile else "") or ""
    restrictions = list(getattr(profile, "restrictions", None) or [])
    diet_class = profile_row["diet_class"]
    if diet == "vegan" or "vegan" in restrictions:
        return diet_class == "vegan"
    if diet == "vegetarian" or "vegetarian" in restrictions:
        return diet_class in {"veg", "vegan"}
    if diet == "eggetarian":
        return diet_class in {"veg", "vegan", "egg"}
    return True


def _region_ok(profile_row: dict, cuisines: list[str]) -> bool:
    if not cuisines:
        return True
    folded = [name.casefold() for name in cuisines]
    south = any(any(hint in name for hint in SOUTH_HINTS) for name in folded)
    north = any(any(hint in name for hint in NORTH_HINTS) for name in folded)
    if south and not north and profile_row["region"] == "north":
        return False
    if north and not south and profile_row["region"] == "south":
        return False
    tags = [tag.casefold() for tag in profile_row.get("cuisine_tags") or []]
    if tags and not any(cuisine.casefold() in tag or tag in cuisine.casefold() for cuisine in folded for tag in tags):
        return profile_row["region"] == "any"
    return True


def _candidates(user, profile, *, include_user_foods: bool) -> list[dict]:
    likes = {name.casefold() for name in (getattr(profile, "likes", None) or [])}
    cuisines = list(getattr(profile, "preferred_cuisines", None) or [])
    avoid_sweets = (getattr(profile, "goal", "") or "") in {"lose", "maintain"}
    rows = []
    for food in Food.objects.all().order_by("food_name")[:900]:
        allowed, reason = suggestion_allowed(name=food.food_name, ingredients="", profile=profile)
        if not allowed:
            continue
        meta = profile_for(food)
        if not _diet_ok(meta, profile):
            continue
        if not _region_ok(meta, cuisines):
            continue
        if avoid_sweets and meta["is_sweet"]:
            continue
        try:
            result = calculate_nutrition(food.food_code, Decimal("100"), "g")
        except NutritionError:
            continue
        energy = result["nutrients"].get("energy_kcal")
        if energy is None:
            continue
        liked = any(like and like in food.food_name.casefold() for like in likes)
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
                "liked": liked,
                "course": meta["course"],
                "region": meta["region"],
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
            liked = any(like and like in user_food.name.casefold() for like in likes)
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
                    "liked": liked,
                    "course": "any",
                    "region": "any",
                }
            )
    rows.sort(key=lambda item: (0 if item["liked"] else 1, item["energy"]))
    return rows


def _assign_slots(candidates: list[dict], calorie_budget: Decimal, profile: UserProfile | None) -> dict:
    assigned = {}
    used = set()
    remaining = calorie_budget
    chosen_region = None
    cuisines = list(getattr(profile, "preferred_cuisines", None) or [])
    south_only = bool(cuisines) and any("south" in name.casefold() for name in cuisines) and not any("north" in name.casefold() or "punjabi" in name.casefold() for name in cuisines)
    north_only = bool(cuisines) and any("north" in name.casefold() or "punjabi" in name.casefold() for name in cuisines) and not any("south" in name.casefold() for name in cuisines)
    for slot in SLOTS:
        share = remaining * SLOT_SHARE[slot] if remaining > 0 else Decimal("0")
        pick = None
        best = None
        for index, item in enumerate(candidates):
            key = ("c", item.get("food_code")) if item.get("food_code") else ("u", item.get("user_food_id"))
            if key in used:
                continue
            if item["course"] not in {slot, "any"} and item["course"] != "snack":
                if slot != PlannedSlot.Slot.SNACK:
                    continue
            if chosen_region and item["region"] not in {chosen_region, "any"}:
                continue
            if south_only and item["region"] == "north":
                continue
            if north_only and item["region"] == "south":
                continue
            distance = abs(item["energy"] - share)
            rank = (0 if item["liked"] else 1, distance)
            if best is None or rank < best[0]:
                best = (rank, index, item, key)
        if best is None:
            for index, item in enumerate(candidates):
                key = ("c", item.get("food_code")) if item.get("food_code") else ("u", item.get("user_food_id"))
                if key in used:
                    continue
                if south_only and item["region"] == "north":
                    continue
                if north_only and item["region"] == "south":
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
        if pick["region"] in {"south", "north"}:
            chosen_region = chosen_region or pick["region"]
    return assigned
