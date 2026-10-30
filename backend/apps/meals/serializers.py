from rest_framework import serializers

from .models import Meal, MealItem


class MealItemInputSerializer(serializers.Serializer):
    food_code = serializers.CharField(required=False, allow_blank=True)
    user_food_id = serializers.IntegerField(required=False)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit = serializers.CharField()
    input_source = serializers.ChoiceField(choices=MealItem.InputSource.choices, required=False)
    confidence = serializers.DecimalField(
        max_digits=4, decimal_places=3, min_value=0, max_value=1, required=False, allow_null=True
    )

    def validate(self, attrs):
        food_code = str(attrs.get("food_code") or "").strip()
        user_food_id = attrs.get("user_food_id")
        if bool(food_code) == bool(user_food_id):
            raise serializers.ValidationError("Provide either a catalogue food or a personal food, not both.")
        attrs["food_code"] = food_code
        return attrs


class MealItemSerializer(serializers.ModelSerializer):
    food_code = serializers.SerializerMethodField()
    food_name = serializers.SerializerMethodField()
    user_food_id = serializers.IntegerField(read_only=True)
    provenance = serializers.SerializerMethodField()

    class Meta:
        model = MealItem
        fields = (
            "id",
            "food_code",
            "food_name",
            "user_food_id",
            "provenance",
            "quantity",
            "unit",
            "input_source",
            "confidence",
            "nutrition_snapshot",
            "dataset_version",
            "calculation_version",
        )

    def get_food_code(self, obj):
        return obj.food.food_code if obj.food_id else ""

    def get_food_name(self, obj):
        if obj.user_food_id:
            return obj.user_food.name
        return obj.food.food_name if obj.food_id else ""

    def get_provenance(self, obj):
        return "user_provided" if obj.user_food_id else "verified"


class MealSerializer(serializers.ModelSerializer):
    items = MealItemSerializer(many=True, read_only=True)

    class Meta:
        model = Meal
        fields = ("id", "timestamp", "meal_type", "created_at", "items")


class MealWriteSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField(required=False)
    meal_type = serializers.ChoiceField(choices=Meal.MealType.choices, required=False)
    items = MealItemInputSerializer(many=True)
