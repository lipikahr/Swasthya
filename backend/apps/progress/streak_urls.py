from django.urls import path

from .views import StreakView

urlpatterns = [
    path("", StreakView.as_view(), name="streaks"),
]
