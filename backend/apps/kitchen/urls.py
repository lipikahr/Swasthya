from django.urls import path

from .views import (
    GroceryGenerateView,
    GroceryItemCreateView,
    GroceryItemDetailView,
    GroceryListView,
    HomeView,
    PlanEntryCreateView,
    PlanEntryDetailView,
    PlanWeekView,
    RecipeDetailView,
    RecipeListView,
    SavedRecipeListView,
    SavedRecipeToggleView,
    SuggestionView,
)

urlpatterns = [
    path("home/", HomeView.as_view(), name="home"),
    path("suggestions/", SuggestionView.as_view(), name="suggestions"),
    path("recipes/", RecipeListView.as_view(), name="recipes"),
    path("recipes/saved/", SavedRecipeListView.as_view(), name="recipes-saved"),
    path("recipes/<slug:slug>/", RecipeDetailView.as_view(), name="recipe-detail"),
    path("recipes/<slug:slug>/save/", SavedRecipeToggleView.as_view(), name="recipe-save"),
    path("plans/", PlanWeekView.as_view(), name="plans"),
    path("plans/entries/", PlanEntryCreateView.as_view(), name="plan-entries"),
    path("plans/entries/<int:entry_id>/", PlanEntryDetailView.as_view(), name="plan-entry"),
    path("groceries/", GroceryListView.as_view(), name="groceries"),
    path("groceries/items/", GroceryItemCreateView.as_view(), name="grocery-items"),
    path("groceries/items/<int:item_id>/", GroceryItemDetailView.as_view(), name="grocery-item"),
    path("groceries/generate/", GroceryGenerateView.as_view(), name="grocery-generate"),
]
