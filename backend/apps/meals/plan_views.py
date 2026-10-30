from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DayPlan, PlannedSlot
from .plan_services import accept_swap, generate_day_plan, get_or_none_plan, seed_log_this, serialize_plan, swap_slot


def _day(request):
    raw = request.query_params.get("date") or request.data.get("date")
    if not raw:
        return timezone.now().date()
    parsed = parse_date(str(raw))
    if parsed is None:
        raise ValidationError({"date": ["Use YYYY-MM-DD."]})
    return parsed


class DayPlanView(APIView):
    def get(self, request):
        return Response(serialize_plan(get_or_none_plan(request.user, _day(request))))

    def post(self, request):
        include = str(request.data.get("include_user_foods") or "1") not in {"0", "false"}
        return Response(generate_day_plan(request.user, _day(request), include_user_foods=include), status=201)


class DayPlanSwapView(APIView):
    def get(self, request, slot_id):
        slot = get_object_or_404(PlannedSlot.objects.select_related("plan"), pk=slot_id, plan__user=request.user)
        return Response(swap_slot(request.user, slot))

    def post(self, request, slot_id):
        slot = get_object_or_404(PlannedSlot.objects.select_related("plan"), pk=slot_id, plan__user=request.user)
        accept_swap(
            request.user,
            slot,
            food_code=str(request.data.get("food_code") or ""),
            user_food_id=request.data.get("user_food_id"),
        )
        plan = DayPlan.objects.prefetch_related("slots__food", "slots__user_food").get(pk=slot.plan_id)
        return Response(serialize_plan(plan))


class DayPlanLogView(APIView):
    def post(self, request, slot_id):
        slot = get_object_or_404(PlannedSlot.objects.select_related("plan", "food", "user_food"), pk=slot_id, plan__user=request.user)
        return Response(seed_log_this(request.user, slot))
