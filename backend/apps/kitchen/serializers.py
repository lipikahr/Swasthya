from rest_framework import serializers

from .models import PlannedMeal


class PlannedMealWriteSerializer(serializers.Serializer):
    date = serializers.DateField()
    slot = serializers.ChoiceField(choices=PlannedMeal.Slot.choices)
    recipe_slug = serializers.SlugField()
    servings = serializers.DecimalField(max_digits=8, decimal_places=3, min_value=0)

    def validate_servings(self, value):
        if value <= 0:
            raise serializers.ValidationError("Servings must be greater than zero.")
        return value


class PlannedMealPatchSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    slot = serializers.ChoiceField(choices=PlannedMeal.Slot.choices, required=False)
    servings = serializers.DecimalField(max_digits=8, decimal_places=3, required=False)

    def validate_servings(self, value):
        if value <= 0:
            raise serializers.ValidationError("Servings must be greater than zero.")
        return value


class GroceryItemWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit = serializers.CharField(max_length=32)
    purchased = serializers.BooleanField(required=False)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("A name is required.")
        return cleaned

    def validate_unit(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("A unit is required.")
        return cleaned


class GroceryGenerateSerializer(serializers.Serializer):
    week = serializers.DateField(required=False)
