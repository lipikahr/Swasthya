from rest_framework import serializers

from .models import NutritionTarget


class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionTarget
        fields = (
            "id",
            "source",
            "effective_from",
            "effective_until",
            "calories",
            "protein_g",
            "carbohydrates_g",
            "fat_g",
            "fibre_g",
        )


class CustomizeSerializer(serializers.Serializer):
    calories = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=1)
    protein_g = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    carbohydrates_g = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    fat_g = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    fibre_g = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
