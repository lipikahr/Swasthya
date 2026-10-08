from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Body and goal details. Login identity stays on the user account."""

    class Sex(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    class Activity(models.TextChoices):
        SEDENTARY = "sedentary", "Sedentary"
        LIGHTLY_ACTIVE = "lightly_active", "Lightly active"
        MODERATELY_ACTIVE = "moderately_active", "Moderately active"
        VERY_ACTIVE = "very_active", "Very active"

    class Goal(models.TextChoices):
        MAINTAIN = "maintain", "Maintain"
        LOSE = "lose", "Lose weight"
        GAIN = "gain", "Gain weight"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    date_of_birth = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=16, choices=Sex.choices, blank=True)
    height_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    activity_level = models.CharField(max_length=32, choices=Activity.choices, blank=True)
    goal = models.CharField(max_length=16, choices=Goal.choices, blank=True)

    def __str__(self) -> str:
        return f"Profile {self.user_id}"
