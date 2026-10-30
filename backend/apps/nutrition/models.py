from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from .nutrients import NUTRIENT_FIELDS


def _nutrient_field():
    # Null means the dataset has no value. Zero means the dataset says zero.
    return models.DecimalField(max_digits=30, decimal_places=15, null=True, blank=True)


class NutritionDatasetVersion(models.Model):
    """One immutable publication of the verified nutrition source."""

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=150)
    source_filename = models.CharField(max_length=255)
    nutrient_basis = models.CharField(max_length=32)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.code


class Food(models.Model):
    """Stable food identity. Nutrition numbers live on FoodNutrition."""

    food_code = models.CharField(max_length=32, unique=True)
    food_name = models.CharField(max_length=255)
    primary_source = models.CharField(max_length=64, blank=True)
    serving_unit = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["food_name", "food_code"]

    def __str__(self) -> str:
        return f"{self.food_code} {self.food_name}"


class FoodAlias(models.Model):
    """A name that points at a canonical Anuvaad food. Unverified aliases are not catalogue rows."""

    class Source(models.TextChoices):
        CURATED = "curated", "Curated"
        USER = "user", "User"
        MODEL = "model", "Model"

    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name="aliases")
    alias_text = models.CharField(max_length=255)
    language = models.CharField(max_length=16)
    normalized_alias = models.CharField(max_length=255, db_index=True)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.CURATED)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["language", "alias_text", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["food", "normalized_alias", "language"],
                name="unique_food_alias_per_language",
            )
        ]

    def save(self, *args, **kwargs):
        from .normalize import normalize_alias

        self.alias_text = str(self.alias_text or "").strip()
        self.normalized_alias = normalize_alias(self.alias_text)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.language}:{self.alias_text} -> {self.food.food_code}"


class UserFood(models.Model):
    """Personal food. Nutrition is user-provided and is not an Anuvaad record."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_foods")
    name = models.CharField(max_length=200)
    ingredients = models.TextField(blank=True, default="")
    serving_amount = models.DecimalField(max_digits=12, decimal_places=3)
    serving_unit = models.CharField(max_length=64)
    energy_kcal = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    protein_g = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    carb_g = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    fat_g = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    fibre_g = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    nutrition_source = models.CharField(max_length=32, default="user_provided")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return f"{self.user_id} {self.name}"


class NutrientValues(models.Model):
    energy_kcal = _nutrient_field()
    carb_g = _nutrient_field()
    protein_g = _nutrient_field()
    fat_g = _nutrient_field()
    fibre_g = _nutrient_field()
    calcium_mg = _nutrient_field()
    iron_mg = _nutrient_field()
    magnesium_mg = _nutrient_field()
    potassium_mg = _nutrient_field()
    sodium_mg = _nutrient_field()
    zinc_mg = _nutrient_field()
    vita_ug = _nutrient_field()
    vitb1_mg = _nutrient_field()
    vitb2_mg = _nutrient_field()
    vitb3_mg = _nutrient_field()
    vitb6_mg = _nutrient_field()
    folate_ug = _nutrient_field()
    vitc_mg = _nutrient_field()
    vitd2_ug = _nutrient_field()
    vitd3_ug = _nutrient_field()
    vite_mg = _nutrient_field()
    vitk1_ug = _nutrient_field()
    vitk2_ug = _nutrient_field()

    class Meta:
        abstract = True

    def as_dict(self) -> dict:
        return {name: getattr(self, name) for name in NUTRIENT_FIELDS}


class FoodNutrition(NutrientValues):
    """Per-100g nutrients for one food in one dataset version."""

    food = models.ForeignKey(Food, on_delete=models.PROTECT, related_name="nutrition_rows")
    dataset_version = models.ForeignKey(
        NutritionDatasetVersion, on_delete=models.PROTECT, related_name="food_nutrition"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["food", "dataset_version"],
                name="unique_food_nutrition_per_version",
            )
        ]


class FoodEmbedding(models.Model):
    """Vector for food search. Nutrition facts stay on FoodNutrition."""

    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name="embeddings")
    dataset_version = models.ForeignKey(
        NutritionDatasetVersion, on_delete=models.CASCADE, related_name="embeddings"
    )
    embedding = VectorField(dimensions=384)
    text_representation = models.TextField()
    language = models.CharField(max_length=16, default="mul")
    model_name = models.CharField(max_length=128)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["food", "dataset_version", "model_name"],
                name="unique_food_embedding_per_model",
            )
        ]


class FoodProfile(models.Model):
    """Catalogue metadata used by the day-plan generator. Not a nutrition source."""

    food = models.OneToOneField(Food, on_delete=models.CASCADE, related_name="profile")
    course = models.CharField(max_length=16, default="any")
    region = models.CharField(max_length=16, default="any")
    diet_class = models.CharField(max_length=16, default="veg")
    is_sweet = models.BooleanField(default=False)
    is_fried = models.BooleanField(default=False)
    cuisine_tags = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return f"{self.food.food_code} {self.course}/{self.region}"


class FoodServingNutrition(NutrientValues):
    """Per-serving nutrients. Created only when the dataset names the serving unit."""

    food = models.ForeignKey(Food, on_delete=models.PROTECT, related_name="serving_rows")
    dataset_version = models.ForeignKey(
        NutritionDatasetVersion, on_delete=models.PROTECT, related_name="serving_nutrition"
    )
    serving_unit = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["food", "dataset_version"],
                name="unique_food_serving_per_version",
            )
        ]
