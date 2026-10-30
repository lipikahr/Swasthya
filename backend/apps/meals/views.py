from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import serializers as drf
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.progress.goal import sync_achievement_for_day

from .models import Meal
from .serializers import MealSerializer, MealWriteSerializer
from .services import create_food_log, replace_meal_items


def _own_meals(user):
    return Meal.objects.filter(user=user).prefetch_related("items__food", "items__user_food")


class MealListCreateView(APIView):
    def get(self, request):
        meals = _own_meals(request.user)
        raw_date = request.query_params.get("date")
        if raw_date:
            parsed = parse_date(raw_date)
            if parsed is None:
                raise ValidationError({"date": ["Use YYYY-MM-DD."]})
            meals = meals.filter(timestamp__date=parsed)
        return Response({"results": MealSerializer(meals, many=True).data})

    def post(self, request):
        serializer = MealWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        meal = create_food_log(
            user=request.user,
            items=data["items"],
            meal_type=data.get("meal_type", Meal.MealType.UNSPECIFIED),
            timestamp=data.get("timestamp"),
            input_source="manual",
        )
        meal = _own_meals(request.user).get(pk=meal.pk)
        return Response(MealSerializer(meal).data, status=201)


class MealDetailView(APIView):
    def get(self, request, meal_id):
        meal = get_object_or_404(_own_meals(request.user), pk=meal_id)
        return Response(MealSerializer(meal).data)

    def patch(self, request, meal_id):
        meal = get_object_or_404(_own_meals(request.user), pk=meal_id)
        if "meal_type" in request.data:
            if request.data["meal_type"] not in Meal.MealType.values:
                raise ValidationError({"meal_type": ["Choose a valid meal type."]})
            meal.meal_type = request.data["meal_type"]
        if "timestamp" in request.data:
            meal.timestamp = drf.DateTimeField().run_validation(request.data["timestamp"])
        if "items" in request.data:
            item_serializer = MealWriteSerializer(data={"items": request.data["items"]})
            item_serializer.is_valid(raise_exception=True)
            replace_meal_items(meal=meal, items=item_serializer.validated_data["items"])
        meal.save(update_fields=["meal_type", "timestamp"])
        meal = _own_meals(request.user).get(pk=meal.pk)
        sync_achievement_for_day(request.user, meal.timestamp.date())
        return Response(MealSerializer(meal).data)

    def delete(self, request, meal_id):
        meal = get_object_or_404(Meal.objects.filter(user=request.user), pk=meal_id)
        day = meal.timestamp.date()
        meal.delete()
        sync_achievement_for_day(request.user, day)
        return Response(status=204)
