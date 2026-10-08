from rest_framework import serializers

from .models import Meal, MealItem


class MealItemInputSerializer(serializers.Serializer):
    food_code = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit = serializers.CharField()
    input_source = serializers.ChoiceField(choices=MealItem.InputSource.choices, required=False)
    confidence = serializers.DecimalField(
        max_digits=4, decimal_places=3, min_value=0, max_value=1, required=False, allow_null=True
    )


class MealItemSerializer(serializers.ModelSerializer):
    food_code = serializers.CharField(source="food.food_code", read_only=True)
    food_name = serializers.CharField(source="food.food_name", read_only=True)

    class Meta:
        model = MealItem
        fields = (
            "id",
            "food_code",
            "food_name",
            "quantity",
            "unit",
            "input_source",
            "confidence",
            "nutrition_snapshot",
            "dataset_version",
            "calculation_version",
        )


class MealSerializer(serializers.ModelSerializer):
    items = MealItemSerializer(many=True, read_only=True)

    class Meta:
        model = Meal
        fields = ("id", "timestamp", "meal_type", "created_at", "items")


class MealWriteSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField(required=False)
    meal_type = serializers.ChoiceField(choices=Meal.MealType.choices, required=False)
    items = MealItemInputSerializer(many=True)
