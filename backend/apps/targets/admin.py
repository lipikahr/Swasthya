from django.contrib import admin

from .models import NutritionTarget


@admin.register(NutritionTarget)
class NutritionTargetAdmin(admin.ModelAdmin):
    list_display = ("user", "source", "calories", "effective_from", "effective_until")
