from django.conf import settings
from django.db import models
from django.utils import timezone


class Meal(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACK = "snack", "Snack"
        UNSPECIFIED = "unspecified", "Unspecified"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meals")
    timestamp = models.DateTimeField(default=timezone.now)
    meal_type = models.CharField(max_length=16, choices=MealType.choices, default=MealType.UNSPECIFIED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp", "-id"]

    def __str__(self) -> str:
        return f"{self.user_id} {self.meal_type} {self.timestamp}"


class MealItem(models.Model):
    class InputSource(models.TextChoices):
        TEXT = "text", "Text"
        VOICE = "voice", "Voice"
        IMAGE = "image", "Image"
        MANUAL = "manual", "Manual"
        SCALE = "scale", "Scale"

    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name="items")
    food = models.ForeignKey("nutrition.Food", on_delete=models.PROTECT, related_name="meal_items")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=64)
    input_source = models.CharField(max_length=16, choices=InputSource.choices, default=InputSource.MANUAL)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    nutrition_snapshot = models.JSONField()
    dataset_version = models.CharField(max_length=64)
    calculation_version = models.CharField(max_length=64)

    def __str__(self) -> str:
        return f"{self.food_id} {self.quantity} {self.unit}"
