from datetime import date
from decimal import Decimal

from rest_framework import serializers

from apps.agent.languages import SUPPORTED_CODES
from apps.nutrition.allergens import normalize_allergen, normalize_restriction

from .models import UserProfile

PROFILE_FIELDS = (
    "date_of_birth",
    "sex",
    "height_cm",
    "weight_kg",
    "activity_level",
    "goal",
)

PREFERENCE_FIELDS = (
    "allergies_status",
    "allergies",
    "dislikes",
    "diet_pattern",
    "preferred_cuisines",
    "preferred_language",
    "appearance",
    "restrictions",
    "likes",
    "notes",
    "autoplay_replies",
)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = PROFILE_FIELDS + PREFERENCE_FIELDS

    def validate_date_of_birth(self, value):
        if value is not None and value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def validate_height_cm(self, value):
        return _positive(value, "Height")

    def validate_weight_kg(self, value):
        return _positive(value, "Weight")

    def validate_allergies(self, value):
        return _string_list(value)

    def validate_dislikes(self, value):
        return _string_list(value)

    def validate_preferred_cuisines(self, value):
        return _string_list(value)

    def validate_allergies_status(self, value):
        allowed = {"", "none", "listed"}
        text = str(value or "")
        if text not in allowed:
            raise serializers.ValidationError("Choose whether allergies are not yet provided, none, or listed.")
        return text

    def validate_preferred_language(self, value):
        code = str(value or "en").strip() or "en"
        if code not in SUPPORTED_CODES:
            raise serializers.ValidationError("Choose a supported language.")
        return code

    def validate_appearance(self, value):
        text = str(value or "light").strip() or "light"
        if text not in {"light", "dark", "system"}:
            raise serializers.ValidationError("Choose light, dark, or system.")
        return text

    def validate_restrictions(self, value):
        items = _string_list(value)
        return [normalize_restriction(item) for item in items if normalize_restriction(item)]

    def validate_likes(self, value):
        return _string_list(value)

    def validate_notes(self, value):
        return str(value or "")[:2000]

    def validate_autoplay_replies(self, value):
        return bool(value)

    def validate(self, attrs):
        status = attrs.get("allergies_status", getattr(self.instance, "allergies_status", ""))
        allergies = attrs.get("allergies", getattr(self.instance, "allergies", []) if self.instance else [])
        cleaned = [normalize_allergen(item) for item in allergies if normalize_allergen(item)]
        if status == "listed" and not cleaned:
            raise serializers.ValidationError({"allergies": ["Add at least one allergy, or choose no allergies declared."]})
        if status == "none":
            attrs["allergies"] = []
        elif "allergies" in attrs:
            attrs["allergies"] = cleaned
        return attrs


def _string_list(value):
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError("Send a list of names.")
    items = []
    for raw in value:
        text = " ".join(str(raw or "").split())
        if text:
            items.append(text[:80])
    return items[:30]


def _positive(value, label):
    if value is not None and value <= Decimal("0"):
        raise serializers.ValidationError(f"{label} must be greater than zero.")
    return value
