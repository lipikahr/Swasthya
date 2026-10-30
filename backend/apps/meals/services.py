from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.nutrition.calculation import NutritionError, calculate_nutrition, calculate_user_food
from apps.nutrition.models import Food, UserFood

from .models import Meal, MealItem


def create_food_log(*, user, items: list[dict], meal_type: str = Meal.MealType.UNSPECIFIED, timestamp=None, input_source: str = "manual") -> Meal:
    if not items:
        error = APIException("Add at least one food.")
        error.status_code = 400
        error.default_code = "empty_meal"
        raise error
    prepared = [_prepare_item(item, input_source, user=user) for item in items]
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
    prepared = [_prepare_item(item, input_source, user=meal.user) for item in items]
    with transaction.atomic():
        meal.items.all().delete()
        for item in prepared:
            MealItem.objects.create(meal=meal, **item)
    return meal


def _source(item: dict, default_source: str) -> str:
    source = item.get("input_source") or default_source
    return source if source in MealItem.InputSource.values else default_source


def _prepare_item(item: dict, default_source: str, user=None) -> dict:
    confidence = item.get("confidence")
    source = _source(item, default_source)
    if item.get("user_food_id"):
        try:
            owned = UserFood.objects.filter(pk=item["user_food_id"])
            if user is not None:
                owned = owned.filter(user=user)
            user_food = owned.get()
            result = calculate_user_food(user_food, item["quantity"], item["unit"])
        except UserFood.DoesNotExist as exc:
            error = APIException("That personal food was not found.")
            error.status_code = 400
            error.default_code = "food_not_found"
            raise error from exc
        except NutritionError as exc:
            error = APIException(str(exc))
            error.status_code = 400
            error.default_code = exc.code
            raise error from exc
        return {
            "food": None,
            "user_food": user_food,
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
    try:
        result = calculate_nutrition(item["food_code"], item["quantity"], item["unit"])
    except NutritionError as exc:
        error = APIException(str(exc))
        error.status_code = 400
        error.default_code = exc.code
        raise error from exc
    food = Food.objects.get(food_code=result["food_code"])
    return {
        "food": food,
        "user_food": None,
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
