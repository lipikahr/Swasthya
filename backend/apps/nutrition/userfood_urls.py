from django.urls import path

from .userfood_views import UserFoodDetailView, UserFoodListCreateView

urlpatterns = [
    path("", UserFoodListCreateView.as_view(), name="user-foods"),
    path("<int:food_id>/", UserFoodDetailView.as_view(), name="user-food-detail"),
]
