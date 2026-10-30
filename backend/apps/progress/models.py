from django.conf import settings
from django.db import models


class DailyGoalAchievement(models.Model):
    """One record per user and local calendar day when the calorie goal is first met."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goal_achievements")
    day = models.DateField()
    meal = models.ForeignKey("meals.Meal", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "day"], name="one_goal_achievement_per_user_day")]
        ordering = ["-day"]
