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
    food = models.ForeignKey("nutrition.Food", null=True, blank=True, on_delete=models.PROTECT, related_name="meal_items")
    user_food = models.ForeignKey(
        "nutrition.UserFood", null=True, blank=True, on_delete=models.PROTECT, related_name="meal_items"
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=64)
    input_source = models.CharField(max_length=16, choices=InputSource.choices, default=InputSource.MANUAL)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    nutrition_snapshot = models.JSONField()
    dataset_version = models.CharField(max_length=64)
    calculation_version = models.CharField(max_length=64)

    def __str__(self) -> str:
        return f"{self.food_id or self.user_food_id} {self.quantity} {self.unit}"


class DayPlan(models.Model):
    """One planned day. Planned slots are not consumed meals."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="day_plans")
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "date"], name="one_day_plan_per_user_date")]
        ordering = ["-date"]


class PlannedSlot(models.Model):
    class Slot(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        SNACK = "snack", "Snack"
        DINNER = "dinner", "Dinner"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        SWAPPED = "swapped", "Swapped"
        LOGGED = "logged", "Logged"

    plan = models.ForeignKey(DayPlan, on_delete=models.CASCADE, related_name="slots")
    slot = models.CharField(max_length=16, choices=Slot.choices)
    food = models.ForeignKey("nutrition.Food", null=True, blank=True, on_delete=models.PROTECT)
    user_food = models.ForeignKey("nutrition.UserFood", null=True, blank=True, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=64)
    nutrition_snapshot = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    logged_meal = models.ForeignKey("meals.Meal", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["plan", "slot"], name="one_slot_per_day_plan")]
        ordering = ["id"]
