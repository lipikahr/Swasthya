from django.conf import settings
from django.db import models


class NutritionTarget(models.Model):
    class Source(models.TextChoices):
        SYSTEM_SUGGESTED = "system_suggested", "System suggested"
        USER_CUSTOMIZED = "user_customized", "User customized"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="targets")
    source = models.CharField(max_length=32, choices=Source.choices)
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)
    calories = models.DecimalField(max_digits=8, decimal_places=2)
    protein_g = models.DecimalField(max_digits=8, decimal_places=2)
    carbohydrates_g = models.DecimalField(max_digits=8, decimal_places=2)
    fat_g = models.DecimalField(max_digits=8, decimal_places=2)
    fibre_g = models.DecimalField(max_digits=8, decimal_places=2)
    weekly_calories = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weekly_protein_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weekly_carbohydrates_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weekly_fat_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weekly_fibre_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(effective_until__isnull=True),
                name="one_open_target_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.source}"
