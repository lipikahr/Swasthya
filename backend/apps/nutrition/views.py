from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .calculation import NutritionError, active_version
from .models import FoodNutrition, FoodServingNutrition, UserFood
from .search import search_food, suggest_foods
from .serializers import FoodDetailSerializer, FoodSummarySerializer


def _dataset_error(exc: NutritionError) -> APIException:
    error = APIException(detail=str(exc))
    error.status_code = 503
    error.default_code = exc.code
    return error


class FoodSearchView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter(name="q", required=True, type=str)],
        responses={200: FoodSummarySerializer(many=True)},
    )
    def get(self, request):
        query = request.query_params.get("q", "")
        if not query.strip():
            raise ValidationError({"q": ["Enter a food name or food code."]})
        try:
            cap = min(max(int(request.query_params.get("limit") or 25), 1), 25)
        except (TypeError, ValueError):
            cap = 25
        try:
            foods = (
                suggest_foods(query, cap)
                if str(request.query_params.get("suggest") or "") in {"1", "true"}
                else search_food(query, cap)
            )
        except NutritionError as exc:
            raise _dataset_error(exc) from exc
        payload = FoodSummarySerializer(foods, many=True).data
        for row in payload:
            row["provenance"] = "verified"
            row["user_food_id"] = None
        if request.user.is_authenticated:
            personal = UserFood.objects.filter(user=request.user, name__icontains=query).order_by("name")[:5]
            extras = [
                {
                    "food_code": "",
                    "food_name": food.name,
                    "primary_source": "user_provided",
                    "serving_unit": food.serving_unit,
                    "provenance": "user_provided",
                    "user_food_id": food.id,
                }
                for food in personal
            ]
            payload = extras + payload
        return Response({"results": payload})


class FoodDetailView(APIView):
    @extend_schema(responses={200: FoodDetailSerializer})
    def get(self, request, food_code):
        try:
            version = active_version()
        except NutritionError as exc:
            raise _dataset_error(exc) from exc
        nutrition = get_object_or_404(
            FoodNutrition.objects.select_related("food", "dataset_version"),
            food__food_code=food_code,
            dataset_version=version,
        )
        serving = FoodServingNutrition.objects.filter(
            food=nutrition.food, dataset_version=version
        ).first()
        payload = {
            "food_code": nutrition.food.food_code,
            "food_name": nutrition.food.food_name,
            "primary_source": nutrition.food.primary_source,
            "serving_unit": nutrition.food.serving_unit,
            "dataset_version": version.code,
            "nutrient_basis": version.nutrient_basis,
            "nutrients": nutrition,
            "serving": None
            if serving is None
            else {"unit": serving.serving_unit, "nutrients": serving},
        }
        return Response(FoodDetailSerializer(payload).data)
