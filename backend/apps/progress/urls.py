from django.urls import path

from .views import DailyProgressView, RangeProgressView

urlpatterns = [
    path("daily/", DailyProgressView.as_view(), name="progress-daily"),
    path("range/", RangeProgressView.as_view(), name="progress-range"),
]
