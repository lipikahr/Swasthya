"""Deterministic nutrition math.

Weight uses the per-100g row: grams / 100. A named serving uses the per-serving
row times the number of servings. Missing nutrients stay missing. This module
does not invent a gram weight for bowl, plate, glass, or spoon.
"""

from decimal import Decimal, InvalidOperation

from .models import Food, FoodNutrition, FoodServingNutrition, NutritionDatasetVersion
from .nutrients import CALCULATION_VERSION, NUTRIENT_FIELDS

WEIGHT_TO_GRAMS = {
    "g": Decimal("1"),
    "gram": Decimal("1"),
    "grams": Decimal("1"),
    "kg": Decimal("1000"),
    "kilogram": Decimal("1000"),
    "kilograms": Decimal("1000"),
}


class NutritionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def active_version() -> NutritionDatasetVersion:
    version = NutritionDatasetVersion.objects.filter(is_active=True).first()
    if version is None:
        raise NutritionError("no_active_dataset", "No nutrition dataset is loaded.")
    return version


def get_food_nutrition(food_code: str) -> FoodNutrition:
    version = active_version()
    try:
        return FoodNutrition.objects.select_related("food", "dataset_version").get(
            food__food_code=food_code,
            dataset_version=version,
        )
    except FoodNutrition.DoesNotExist as exc:
        raise NutritionError("food_not_found", f"No food with code {food_code}.") from exc


def calculate_nutrition(food_code: str, quantity, unit: str) -> dict:
    if quantity is None or (isinstance(quantity, str) and quantity.strip() == ""):
        raise NutritionError("missing_quantity", "A quantity is required.")
    try:
        amount = Decimal(str(quantity))
    except (InvalidOperation, ValueError) as exc:
        raise NutritionError("invalid_quantity", "Quantity must be a number.") from exc
    if amount <= 0:
        raise NutritionError("invalid_quantity", "Quantity must be greater than zero.")

    nutrition = get_food_nutrition(food_code)
    food = nutrition.food
    normalized_unit = (unit or "").strip().lower()
    if not normalized_unit:
        raise NutritionError("unsupported_unit", "A unit is required.")

    if normalized_unit in WEIGHT_TO_GRAMS:
        grams = amount * WEIGHT_TO_GRAMS[normalized_unit]
        nutrients = _scale(nutrition.as_dict(), grams / Decimal("100"))
        basis = "per_100g"
        applied_unit = "g" if WEIGHT_TO_GRAMS[normalized_unit] == 1 else "kg"
    else:
        serving = _matching_serving(food, nutrition.dataset_version, normalized_unit)
        nutrients = _scale(serving.as_dict(), amount)
        basis = "per_serving"
        applied_unit = serving.serving_unit

    return {
        "food_code": food.food_code,
        "food_name": food.food_name,
        "quantity": amount,
        "unit": applied_unit,
        "basis": basis,
        "calculation_version": CALCULATION_VERSION,
        "dataset_version": nutrition.dataset_version.code,
        "nutrients": nutrients,
    }


def _matching_serving(food: Food, version, normalized_unit: str) -> FoodServingNutrition:
    serving = (
        FoodServingNutrition.objects.filter(food=food, dataset_version=version)
        .order_by("id")
        .first()
    )
    if serving is None or serving.serving_unit.strip().lower() != normalized_unit:
        verified = serving.serving_unit if serving is not None else ""
        if verified:
            message = (
                f"{food.food_name} can be logged in grams, kilograms, or {verified}. "
                f"{normalized_unit} is not a verified unit for this food."
            )
        else:
            message = (
                f"{food.food_name} can be logged in grams or kilograms. "
                f"{normalized_unit} has no verified serving basis."
            )
        raise NutritionError("unsupported_unit", message)
    return serving


def _scale(nutrients: dict, multiplier: Decimal) -> dict:
    scaled = {}
    for name in NUTRIENT_FIELDS:
        value = nutrients[name]
        scaled[name] = None if value is None else value * multiplier
    return scaled


def calculate_user_food(user_food, quantity, unit: str) -> dict:
    if quantity is None or (isinstance(quantity, str) and quantity.strip() == ""):
        raise NutritionError("missing_quantity", "A quantity is required.")
    try:
        amount = Decimal(str(quantity))
    except (InvalidOperation, TypeError) as exc:
        raise NutritionError("invalid_quantity", "Quantity must be a number.") from exc
    if amount <= 0:
        raise NutritionError("invalid_quantity", "Quantity must be greater than zero.")
    unit_name = (unit or "").strip().lower()
    serving_unit = (user_food.serving_unit or "").strip().lower()
    serving_amount = Decimal(str(user_food.serving_amount))
    if serving_amount <= 0:
        raise NutritionError("invalid_quantity", "Serving amount must be greater than zero.")
    if unit_name in WEIGHT_TO_GRAMS and serving_unit in WEIGHT_TO_GRAMS:
        grams = amount * WEIGHT_TO_GRAMS[unit_name]
        serving_grams = serving_amount * WEIGHT_TO_GRAMS[serving_unit]
        multiplier = grams / serving_grams
        used_unit = unit_name
    elif unit_name == serving_unit:
        multiplier = amount / serving_amount
        used_unit = user_food.serving_unit
    else:
        raise NutritionError(
            "unsupported_unit",
            f"{user_food.name} can be logged in {user_food.serving_unit}. {unit} is not a matching unit.",
        )
    nutrients = {name: None for name in NUTRIENT_FIELDS}
    mapping = {
        "energy_kcal": user_food.energy_kcal,
        "protein_g": user_food.protein_g,
        "carb_g": user_food.carb_g,
        "fat_g": user_food.fat_g,
        "fibre_g": user_food.fibre_g,
    }
    for name, value in mapping.items():
        nutrients[name] = None if value is None else Decimal(str(value)) * multiplier
    return {
        "food_code": None,
        "food_name": user_food.name,
        "quantity": amount,
        "unit": used_unit,
        "basis": "user_serving",
        "dataset_version": "user_provided",
        "calculation_version": CALCULATION_VERSION,
        "nutrients": nutrients,
        "user_food_id": user_food.id,
        "provenance": "user_provided",
    }
