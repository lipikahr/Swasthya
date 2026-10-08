from django.urls import path

from .views import DailyProgressView

urlpatterns = [
    path("daily/", DailyProgressView.as_view(), name="progress-daily"),
]
