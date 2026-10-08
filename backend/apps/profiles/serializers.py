from datetime import date
from decimal import Decimal

from rest_framework import serializers

from .models import UserProfile

PROFILE_FIELDS = (
    "date_of_birth",
    "sex",
    "height_cm",
    "weight_kg",
    "activity_level",
    "goal",
)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = PROFILE_FIELDS

    def validate_date_of_birth(self, value):
        if value is not None and value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def validate_height_cm(self, value):
        return _positive(value, "Height")

    def validate_weight_kg(self, value):
        return _positive(value, "Weight")


def _positive(value, label):
    if value is not None and value <= Decimal("0"):
        raise serializers.ValidationError(f"{label} must be greater than zero.")
    return value
