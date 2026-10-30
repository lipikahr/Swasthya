from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserFood
from .serializers_userfood import UserFoodSerializer, UserFoodWriteSerializer


class UserFoodListCreateView(APIView):
    def get(self, request):
        foods = UserFood.objects.filter(user=request.user)
        return Response({"results": UserFoodSerializer(foods, many=True).data})

    def post(self, request):
        serializer = UserFoodWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        food = UserFood.objects.create(user=request.user, nutrition_source="user_provided", **serializer.validated_data)
        return Response(UserFoodSerializer(food).data, status=201)


class UserFoodDetailView(APIView):
    def get(self, request, food_id):
        food = get_object_or_404(UserFood.objects.filter(user=request.user), pk=food_id)
        return Response(UserFoodSerializer(food).data)

    def patch(self, request, food_id):
        food = get_object_or_404(UserFood.objects.filter(user=request.user), pk=food_id)
        serializer = UserFoodWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for name, value in serializer.validated_data.items():
            setattr(food, name, value)
        food.nutrition_source = "user_provided"
        food.save()
        return Response(UserFoodSerializer(food).data)

    def delete(self, request, food_id):
        food = get_object_or_404(UserFood.objects.filter(user=request.user), pk=food_id)
        if food.meal_items.exists():
            raise ValidationError("This personal food is used in a saved meal, so it cannot be deleted.")
        food.delete()
        return Response(status=204)
