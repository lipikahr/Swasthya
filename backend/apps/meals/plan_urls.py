from django.urls import path

from .plan_views import DayPlanLogView, DayPlanSwapView, DayPlanView

urlpatterns = [
    path("", DayPlanView.as_view(), name="day-plan"),
    path("slots/<int:slot_id>/swap/", DayPlanSwapView.as_view(), name="day-plan-swap"),
    path("slots/<int:slot_id>/log/", DayPlanLogView.as_view(), name="day-plan-log"),
]
