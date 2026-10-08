"""Personalized targets from the project formulas.

These are application defaults, not a medical prescription. The numbers are
computed in code. A language model is not asked to produce them.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

ACTIVITY_FACTORS = {
    "sedentary": Decimal("1.20"),
    "lightly_active": Decimal("1.375"),
    "moderately_active": Decimal("1.55"),
    "very_active": Decimal("1.725"),
}

PROTEIN_PER_KG = {
    "maintain": Decimal("0.8"),
    "lose": Decimal("1.2"),
    "gain": Decimal("1.0"),
}

CALORIE_ADJUSTMENT = {
    "maintain": Decimal("0"),
    "lose": Decimal("-500"),
    "gain": Decimal("300"),
}


class TargetError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def age_in_years(date_of_birth: date, on_date: date) -> int:
    years = on_date.year - date_of_birth.year
    if (on_date.month, on_date.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years


def suggest_targets(*, sex: str, age_years: int, height_cm, weight_kg, activity_level: str, goal: str) -> dict:
    if sex not in {"male", "female"}:
        raise TargetError("profile_incomplete", "Sex must be male or female before targets can be suggested.")
    if age_years < 18 or age_years > 120:
        raise TargetError("profile_incomplete", "Age must be between 18 and 120 to use these defaults.")
    if activity_level not in ACTIVITY_FACTORS or goal not in PROTEIN_PER_KG:
        raise TargetError("profile_incomplete", "Activity level and goal are required.")

    weight = Decimal(weight_kg)
    height = Decimal(height_cm)
    sex_constant = Decimal("5") if sex == "male" else Decimal("-161")
    rmr = (Decimal("10") * weight) + (Decimal("6.25") * height) - (Decimal("5") * age_years) + sex_constant
    tdee = rmr * ACTIVITY_FACTORS[activity_level]
    calories = tdee + CALORIE_ADJUSTMENT[goal]
    if calories <= 0:
        raise TargetError("target_not_viable", "The calorie default would not be positive.")

    protein = weight * PROTEIN_PER_KG[goal]
    fat_calories = calories * Decimal("0.30")
    fat = fat_calories / Decimal("9")
    remaining = calories - (protein * Decimal("4")) - (fat * Decimal("9"))
    if remaining < 0:
        raise TargetError("target_not_viable", "The macro default would leave no room for carbohydrates.")
    carbohydrates = remaining / Decimal("4")
    fibre = calories / Decimal("1000") * Decimal("14")
    return {
        "calories": _quantize(calories, "1"),
        "protein_g": _quantize(protein, "0.01"),
        "carbohydrates_g": _quantize(carbohydrates, "0.01"),
        "fat_g": _quantize(fat, "0.01"),
        "fibre_g": _quantize(fibre, "0.01"),
    }


def _quantize(value: Decimal, places: str) -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)
