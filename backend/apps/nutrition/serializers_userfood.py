from decimal import Decimal

from rest_framework import serializers

from .models import UserFood


class UserFoodSerializer(serializers.ModelSerializer):
    provenance = serializers.SerializerMethodField()
    allergen_status = serializers.SerializerMethodField()

    class Meta:
        model = UserFood
        fields = (
            "id",
            "name",
            "ingredients",
            "serving_amount",
            "serving_unit",
            "energy_kcal",
            "protein_g",
            "carb_g",
            "fat_g",
            "fibre_g",
            "nutrition_source",
            "provenance",
            "allergen_status",
            "created_at",
            "updated_at",
        )

    def get_provenance(self, obj):
        return "user_provided"

    def get_allergen_status(self, obj):
        if str(obj.ingredients or "").strip():
            return "ingredients_listed"
        return "unverified"


class UserFoodWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    ingredients = serializers.CharField(required=False, allow_blank=True, default="")
    serving_amount = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    serving_unit = serializers.CharField(max_length=64)
    energy_kcal = serializers.DecimalField(max_digits=12, decimal_places=3, required=False, allow_null=True)
    protein_g = serializers.DecimalField(max_digits=12, decimal_places=3, required=False, allow_null=True)
    carb_g = serializers.DecimalField(max_digits=12, decimal_places=3, required=False, allow_null=True)
    fat_g = serializers.DecimalField(max_digits=12, decimal_places=3, required=False, allow_null=True)
    fibre_g = serializers.DecimalField(max_digits=12, decimal_places=3, required=False, allow_null=True)
