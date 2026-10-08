from django.urls import path

from .views import FoodDetailView, FoodSearchView

urlpatterns = [
    path("search/", FoodSearchView.as_view(), name="food-search"),
    path("<str:food_code>/", FoodDetailView.as_view(), name="food-detail"),
]
