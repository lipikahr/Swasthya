from rest_framework import serializers

from .models import Food
from .nutrients import NUTRIENT_FIELDS


def _decimal_field():
    return serializers.DecimalField(max_digits=30, decimal_places=15, allow_null=True, read_only=True)


class NutrientSerializer(serializers.Serializer):
    energy_kcal = _decimal_field()
    carb_g = _decimal_field()
    protein_g = _decimal_field()
    fat_g = _decimal_field()
    fibre_g = _decimal_field()
    calcium_mg = _decimal_field()
    iron_mg = _decimal_field()
    magnesium_mg = _decimal_field()
    potassium_mg = _decimal_field()
    sodium_mg = _decimal_field()
    zinc_mg = _decimal_field()
    vita_ug = _decimal_field()
    vitb1_mg = _decimal_field()
    vitb2_mg = _decimal_field()
    vitb3_mg = _decimal_field()
    vitb6_mg = _decimal_field()
    folate_ug = _decimal_field()
    vitc_mg = _decimal_field()
    vitd2_ug = _decimal_field()
    vitd3_ug = _decimal_field()
    vite_mg = _decimal_field()
    vitk1_ug = _decimal_field()
    vitk2_ug = _decimal_field()

    def to_representation(self, instance):
        if isinstance(instance, dict):
            return super().to_representation(instance)
        return super().to_representation({name: getattr(instance, name) for name in NUTRIENT_FIELDS})


class FoodSummarySerializer(serializers.ModelSerializer):
    serving_unit = serializers.CharField(allow_blank=True)

    class Meta:
        model = Food
        fields = ("food_code", "food_name", "primary_source", "serving_unit")


class ServingSerializer(serializers.Serializer):
    unit = serializers.CharField()
    nutrients = NutrientSerializer()


class FoodDetailSerializer(serializers.Serializer):
    food_code = serializers.CharField()
    food_name = serializers.CharField()
    primary_source = serializers.CharField()
    serving_unit = serializers.CharField(allow_blank=True)
    dataset_version = serializers.CharField()
    nutrient_basis = serializers.CharField()
    nutrients = NutrientSerializer()
    serving = ServingSerializer(allow_null=True)
