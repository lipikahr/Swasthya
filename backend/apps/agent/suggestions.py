"""Preference-aware food suggestions. Suggestions are never saved meals."""

import re
from decimal import Decimal

from apps.nutrition.allergens import allergen_conflict, diet_conflict, dislike_conflict, restriction_conflict
from apps.nutrition.calculation import NutritionError, calculate_nutrition
from apps.nutrition.models import Food
from apps.progress.goal import GOAL_ABOVE, GOAL_MET, day_goal_status
from apps.profiles.models import UserProfile

_SUGGEST = re.compile(
    r"(suggest|recommend|confused|what (?:can|should) i eat|what to eat|options|complete today|need more protein|vegetarian meal|for lunch|for breakfast|for dinner)",
    re.IGNORECASE,
)
_LOG = re.compile(r"\b(i ate|i had|i eaten|log )\b", re.IGNORECASE)


def is_suggestion_request(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned or _LOG.search(cleaned):
        return False
    return bool(_SUGGEST.search(cleaned))


def _profile(user) -> UserProfile | None:
    return UserProfile.objects.filter(user=user).first()


def suggest_foods_for_user(user, meal_type: str | None = None) -> dict:
    profile = _profile(user)
    progress = day_goal_status(user)
    allergies_status = getattr(profile, "allergies_status", "") if profile else ""
    allergies = list(getattr(profile, "allergies", None) or []) if profile else []
    dislikes = list(getattr(profile, "dislikes", None) or []) if profile else []
    diet = getattr(profile, "diet_pattern", "") if profile else ""
    restrictions = list(getattr(profile, "restrictions", None) or []) if profile else []
    remaining = progress.get("remaining") or {}
    calorie_status = progress["goal_status"]
    protein_need = remaining.get("protein_g")
    calorie_need = remaining.get("calories")
    if calorie_status in {GOAL_MET, GOAL_ABOVE}:
        return {
            "status": "SUGGESTIONS",
            "reply": "Today's calorie target is already met or exceeded. I will not suggest extra food unless you want to log something you already ate.",
            "suggestions": [],
            "allergy_note": _allergy_note(allergies_status, allergies),
            "meal_id": None,
        }
    candidates = []
    for food in Food.objects.all().order_by("food_name")[:400]:
        if allergen_conflict(food.food_name, allergies):
            continue
        if diet_conflict(food.food_name, diet):
            continue
        if dislike_conflict(food.food_name, dislikes):
            continue
        if restriction_conflict(food.food_name, restrictions):
            continue
        try:
            preview = calculate_nutrition(food.food_code, Decimal("100"), "g")
        except NutritionError:
            continue
        energy = preview["nutrients"].get("energy_kcal")
        protein = preview["nutrients"].get("protein_g")
        if energy is None:
            continue
        if calorie_need is not None and Decimal(str(energy)) > Decimal(str(calorie_need)) + Decimal("80"):
            continue
        if protein_need is not None and protein_need > 0 and (protein is None or protein <= 0):
            continue
        reasons = []
        if protein_need is not None and protein_need > 0 and protein:
            reasons.append("protein remaining")
        if diet:
            reasons.append(diet)
        if meal_type:
            reasons.append(meal_type)
        reasons.append("verified catalogue")
        if allergies_status == "listed":
            reasons.append("ingredient list not verified; not described as allergy-safe")
        candidates.append(
            {
                "food_code": food.food_code,
                "food_name": food.food_name,
                "quantity": "100",
                "unit": "g",
                "nutrition": {name: None if value is None else str(value) for name, value in preview["nutrients"].items()},
                "reasons": reasons,
            }
        )
        if len(candidates) >= 12:
            break
    safe = []
    for item in candidates:
        if allergen_conflict(item["food_name"], allergies):
            continue
        safe.append(item)
        if len(safe) == 3:
            break
    if not safe:
        reply = "I could not find a verified food that also passes your allergy and preference filters."
    else:
        names = ", ".join(item["food_name"] for item in safe)
        reply = f"Here are options from the verified foods: {names}. They are not logged until you confirm a meal."
    return {
        "status": "SUGGESTIONS",
        "reply": reply,
        "suggestions": safe,
        "allergy_note": _allergy_note(allergies_status, allergies),
        "meal_id": None,
    }


def _allergy_note(status: str, allergies: list[str]) -> str:
    if status == "":
        return "Allergy information is not yet provided. Suggestions cannot be treated as allergy-safe."
    if status == "none":
        return "No allergies declared."
    joined = ", ".join(allergies) if allergies else "listed allergies"
    return (
        f"Foods matching {joined} were excluded by name. The nutrition dataset does not include complete ingredient lists, "
        "so remaining options are not confirmed as free of allergens or cross-contamination."
    )
