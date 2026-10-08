from django.urls import path

from .views import MealDetailView, MealListCreateView

urlpatterns = [
    path("", MealListCreateView.as_view(), name="meals"),
    path("<int:meal_id>/", MealDetailView.as_view(), name="meal-detail"),
]
