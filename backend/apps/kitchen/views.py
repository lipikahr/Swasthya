from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GroceryItem, PlannedMeal, Recipe, SavedRecipe
from .serializers import (
    GroceryGenerateSerializer,
    GroceryItemWriteSerializer,
    PlannedMealPatchSerializer,
    PlannedMealWriteSerializer,
)
from .services import (
    add_planned_meal,
    generate_grocery,
    grocery_for,
    grocery_payload,
    home_payload,
    monday,
    recipe_card,
    recipe_detail,
    recipe_queryset,
    saved_id_set,
    stored_servings,
    suggestions_payload,
    week_plan,
)


def _servings_param(request, default: Decimal) -> Decimal:
    raw = request.query_params.get("servings")
    if raw in (None, ""):
        return default
    try:
        servings = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError({"servings": ["Servings must be a number."]}) from exc
    if servings <= 0:
        raise ValidationError({"servings": ["Servings must be greater than zero."]})
    return servings


def _week_param(request):
    from django.utils import timezone
    from django.utils.dateparse import parse_date

    raw = request.query_params.get("week")
    if not raw:
        return monday(timezone.now().date())
    parsed = parse_date(raw)
    if parsed is None:
        raise ValidationError({"week": ["Use YYYY-MM-DD."]})
    return monday(parsed)


class RecipeListView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter("q", str, description="Match title, summary, or ingredient label.")],
        description=(
            "Curated recipes. nutrition_status is complete only when every ingredient "
            "maps to a verified food and a supported quantity."
        ),
    )
    def get(self, request):
        saved = saved_id_set(request.user)
        recipes = recipe_queryset(request.query_params.get("q", "")).prefetch_related("ingredients__food")
        return Response({"results": [recipe_card(recipe, saved) for recipe in recipes]})


class SavedRecipeListView(APIView):
    @extend_schema(description="Recipes this user has saved. Other users' collections are not included.")
    def get(self, request):
        rows = SavedRecipe.objects.filter(user=request.user).select_related("recipe")
        saved = {row.recipe_id for row in rows}
        return Response({"results": [recipe_card(row.recipe, saved) for row in rows]})


class RecipeDetailView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter("servings", str, description="Scale ingredient quantities and nutrition.")],
        description=(
            "Ingredient quantities scale with servings. "
            "nutrition.nutrients is null when the calculation is incomplete."
        ),
    )
    def get(self, request, slug):
        recipe = get_object_or_404(Recipe.objects.prefetch_related("ingredients__food"), slug=slug)
        servings = _servings_param(request, recipe.base_servings)
        return Response(recipe_detail(recipe, request.user, servings))


class SavedRecipeToggleView(APIView):
    @extend_schema(description="Save a recipe for the authenticated user.")
    def post(self, request, slug):
        recipe = get_object_or_404(Recipe, slug=slug)
        _, created = SavedRecipe.objects.get_or_create(user=request.user, recipe=recipe)
        return Response({"saved": True, "slug": recipe.slug}, status=201 if created else 200)

    @extend_schema(description="Remove a recipe from the authenticated user's collection.")
    def delete(self, request, slug):
        recipe = get_object_or_404(Recipe, slug=slug)
        SavedRecipe.objects.filter(user=request.user, recipe=recipe).delete()
        return Response(status=204)


class PlanWeekView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter("week", str, description="Any date in the week. The response starts on Monday.")],
        description="Planned recipes for one week. These entries are not consumed meals.",
    )
    def get(self, request):
        return Response(week_plan(request.user, _week_param(request)))


class PlanEntryCreateView(APIView):
    @extend_schema(request=PlannedMealWriteSerializer, description="Add a recipe to a day and meal slot.")
    def post(self, request):
        serializer = PlannedMealWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        recipe = get_object_or_404(Recipe, slug=data["recipe_slug"])
        entry = add_planned_meal(
            request.user,
            data["date"],
            data["slot"],
            recipe,
            data["servings"],
        )
        return Response({"id": entry.id, "date": entry.date.isoformat(), "slot": entry.slot}, status=201)


class PlanEntryDetailView(APIView):
    @extend_schema(request=PlannedMealPatchSerializer, description="Change servings, slot, or date inside the same week.")
    def patch(self, request, entry_id):
        entry = get_object_or_404(PlannedMeal.objects.filter(plan__user=request.user), pk=entry_id)
        serializer = PlannedMealPatchSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "date" in data:
            start = entry.plan.week_start
            if not start <= data["date"] <= start + timedelta(days=6):
                raise ValidationError({"date": ["Choose a date in this plan week."]})
            entry.date = data["date"]
        if "slot" in data:
            entry.slot = data["slot"]
        if "servings" in data:
            entry.servings = stored_servings(data["servings"])
        entry.save()
        return Response({"id": entry.id, "date": entry.date.isoformat(), "slot": entry.slot, "servings": str(entry.servings)})

    def delete(self, request, entry_id):
        entry = get_object_or_404(PlannedMeal.objects.filter(plan__user=request.user), pk=entry_id)
        entry.delete()
        return Response(status=204)


class GroceryListView(APIView):
    @extend_schema(description="The authenticated user's grocery list, including manual and generated items.")
    def get(self, request):
        return Response(grocery_payload(grocery_for(request.user)))


class GroceryItemCreateView(APIView):
    @extend_schema(request=GroceryItemWriteSerializer, description="Add a manual grocery item.")
    def post(self, request):
        serializer = GroceryItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        item = GroceryItem.objects.create(
            grocery_list=grocery_for(request.user),
            name=data["name"],
            quantity=data["quantity"],
            unit=data["unit"],
            purchased=data.get("purchased", False),
            origin=GroceryItem.Origin.MANUAL,
        )
        return Response({"id": item.id, "origin": item.origin}, status=201)


class GroceryItemDetailView(APIView):
    @extend_schema(request=GroceryItemWriteSerializer, description="Edit a grocery item the user owns.")
    def patch(self, request, item_id):
        item = get_object_or_404(GroceryItem.objects.filter(grocery_list__user=request.user), pk=item_id)
        serializer = GroceryItemWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for field in ("name", "quantity", "unit", "purchased"):
            if field in data:
                setattr(item, field, data[field])
        item.save()
        return Response({"id": item.id, "purchased": item.purchased, "origin": item.origin})

    def delete(self, request, item_id):
        item = get_object_or_404(GroceryItem.objects.filter(grocery_list__user=request.user), pk=item_id)
        item.delete()
        return Response(status=204)


class GroceryGenerateView(APIView):
    @extend_schema(
        request=GroceryGenerateSerializer,
        description=(
            "Replace generated items for the selected week using planned recipes. "
            "Manual items are kept. Matching verified foods are combined only when units are compatible."
        ),
    )
    def post(self, request):
        from django.utils import timezone

        serializer = GroceryGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        week = serializer.validated_data.get("week") or timezone.now().date()
        payload = generate_grocery(request.user, monday(week))
        payload["week_start"] = monday(week).isoformat()
        return Response(payload)


class HomeView(APIView):
    @extend_schema(
        description=(
            "Authenticated home summary. Nutrition totals come from logged meals. "
            "The featured recipe is included only when its ingredient calculation is complete."
        )
    )
    def get(self, request):
        return Response(home_payload(request.user))


class SuggestionView(APIView):
    @extend_schema(
        description=(
            "Nutrient gaps from today's logged meals and active target. "
            "Recipe rows are included only when ingredient nutrition is complete, "
            "and they do not claim to meet the daily goal."
        )
    )
    def get(self, request):
        return Response(suggestions_payload(request.user))
