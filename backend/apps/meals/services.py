from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.nutrition.calculation import NutritionError, calculate_nutrition
from apps.nutrition.models import Food

from .models import Meal, MealItem


def create_food_log(*, user, items: list[dict], meal_type: str = Meal.MealType.UNSPECIFIED, timestamp=None, input_source: str = "manual") -> Meal:
    if not items:
        error = APIException("Add at least one food.")
        error.status_code = 400
        error.default_code = "empty_meal"
        raise error
    prepared = [_prepare_item(item, input_source) for item in items]
    if meal_type not in Meal.MealType.values:
        meal_type = Meal.MealType.UNSPECIFIED
    with transaction.atomic():
        meal = Meal.objects.create(
            user=user,
            timestamp=timestamp or timezone.now(),
            meal_type=meal_type,
        )
        for item in prepared:
            MealItem.objects.create(meal=meal, **item)
    return meal


def replace_meal_items(*, meal: Meal, items: list[dict], input_source: str = "manual") -> Meal:
    prepared = [_prepare_item(item, input_source) for item in items]
    with transaction.atomic():
        meal.items.all().delete()
        for item in prepared:
            MealItem.objects.create(meal=meal, **item)
    return meal


def _prepare_item(item: dict, default_source: str) -> dict:
    try:
        result = calculate_nutrition(item["food_code"], item["quantity"], item["unit"])
    except NutritionError as exc:
        error = APIException(str(exc))
        error.status_code = 400
        error.default_code = exc.code
        raise error from exc
    food = Food.objects.get(food_code=result["food_code"])
    source = item.get("input_source") or default_source
    if source not in MealItem.InputSource.values:
        source = default_source
    confidence = item.get("confidence")
    return {
        "food": food,
        "quantity": result["quantity"],
        "unit": result["unit"],
        "input_source": source,
        "confidence": None if confidence is None else Decimal(str(confidence)),
        "nutrition_snapshot": {
            name: None if value is None else str(value) for name, value in result["nutrients"].items()
        },
        "dataset_version": result["dataset_version"],
        "calculation_version": result["calculation_version"],
    }
