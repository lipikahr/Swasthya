from django.conf import settings
from django.db import models


class Recipe(models.Model):
    """A curated recipe. Nutrition is calculated later and is not stored here."""

    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=200)
    summary = models.TextField()
    instructions = models.TextField()
    base_servings = models.DecimalField(max_digits=6, decimal_places=2)
    source_name = models.CharField(max_length=200)
    source_note = models.TextField()
    license_note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="ingredients")
    food = models.ForeignKey(
        "nutrition.Food",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="recipe_ingredients",
    )
    label = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=32)
    sort_order = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.label} ({self.recipe_id})"


class SavedRecipe(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_recipes")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="saves")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "recipe"], name="unique_saved_recipe"),
        ]
        ordering = ["-created_at"]


class MealPlan(models.Model):
    """A week of planned recipes. This is not a record of food that was eaten."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meal_plans")
    week_start = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "week_start"], name="unique_meal_plan_week"),
        ]
        ordering = ["-week_start"]


class PlannedMeal(models.Model):
    class Slot(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACK = "snack", "Snack"

    plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name="entries")
    date = models.DateField()
    slot = models.CharField(max_length=16, choices=Slot.choices)
    recipe = models.ForeignKey(Recipe, on_delete=models.PROTECT, related_name="planned_meals")
    servings = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "slot", "id"]


class GroceryList(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="grocery_list")
    updated_at = models.DateTimeField(auto_now=True)


class GroceryItem(models.Model):
    class Origin(models.TextChoices):
        MANUAL = "manual", "Manual"
        GENERATED = "generated", "Generated"

    grocery_list = models.ForeignKey(GroceryList, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=32)
    purchased = models.BooleanField(default=False)
    origin = models.CharField(max_length=16, choices=Origin.choices, default=Origin.MANUAL)
    food = models.ForeignKey(
        "nutrition.Food",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="grocery_items",
    )
    week_start = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["purchased", "origin", "name", "id"]
