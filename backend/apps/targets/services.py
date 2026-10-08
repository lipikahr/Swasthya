from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.profiles.models import UserProfile

from .engine import TargetError, age_in_years, suggest_targets
from .models import NutritionTarget


def current_target(user):
    return NutritionTarget.objects.filter(user=user, effective_until__isnull=True).first()


def suggestion_for(user, on_date: date | None = None) -> dict:
    profile = UserProfile.objects.filter(user=user).first()
    if profile is None:
        raise ValidationError("Complete your profile before requesting a target suggestion.")
    required = {
        "date_of_birth": profile.date_of_birth,
        "sex": profile.sex,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "activity_level": profile.activity_level,
        "goal": profile.goal,
    }
    missing = [name for name, value in required.items() if value in (None, "")]
    if missing:
        raise ValidationError({name: ["This field is required before a suggestion."] for name in missing})
    today = on_date or timezone.now().date()
    try:
        numbers = suggest_targets(
            sex=profile.sex,
            age_years=age_in_years(profile.date_of_birth, today),
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            activity_level=profile.activity_level,
            goal=profile.goal,
        )
    except TargetError as exc:
        error = APIException(str(exc))
        error.status_code = 400
        error.default_code = exc.code
        raise error from exc
    return numbers


def accept_suggestion(user) -> NutritionTarget:
    numbers = suggestion_for(user)
    return _replace_open_target(user, NutritionTarget.Source.SYSTEM_SUGGESTED, numbers)


def customize_target(user, numbers: dict) -> NutritionTarget:
    return _replace_open_target(user, NutritionTarget.Source.USER_CUSTOMIZED, numbers)


def _replace_open_target(user, source: str, numbers: dict) -> NutritionTarget:
    now = timezone.now()
    with transaction.atomic():
        NutritionTarget.objects.filter(user=user, effective_until__isnull=True).update(effective_until=now)
        return NutritionTarget.objects.create(
            user=user,
            source=source,
            effective_from=now,
            calories=numbers["calories"],
            protein_g=numbers["protein_g"],
            carbohydrates_g=numbers["carbohydrates_g"],
            fat_g=numbers["fat_g"],
            fibre_g=numbers["fibre_g"],
        )
