from django.contrib import admin

from .models import Food, FoodAlias, FoodNutrition, FoodServingNutrition, NutritionDatasetVersion


@admin.register(NutritionDatasetVersion)
class NutritionDatasetVersionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "nutrient_basis", "is_active", "created_at")


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ("food_code", "food_name", "primary_source", "serving_unit")
    search_fields = ("food_code", "food_name")


@admin.register(FoodAlias)
class FoodAliasAdmin(admin.ModelAdmin):
    list_display = ("alias_text", "language", "food", "verified", "source")
    search_fields = ("alias_text", "normalized_alias", "food__food_name", "food__food_code")
    list_filter = ("language", "verified", "source")


@admin.register(FoodNutrition)
class FoodNutritionAdmin(admin.ModelAdmin):
    list_display = ("food", "dataset_version", "energy_kcal", "protein_g", "carb_g", "fat_g")


@admin.register(FoodServingNutrition)
class FoodServingNutritionAdmin(admin.ModelAdmin):
    list_display = ("food", "dataset_version", "serving_unit", "energy_kcal")
