from django.contrib import admin

from .models import Meal, MealItem


class MealItemInline(admin.TabularInline):
    model = MealItem
    extra = 0


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "meal_type", "timestamp")
    inlines = [MealItemInline]
