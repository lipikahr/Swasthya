from django.urls import path

from .views import (
    AcceptSuggestionView,
    CustomizeTargetView,
    SuggestTargetView,
    TargetCurrentView,
    TargetHistoryView,
)

urlpatterns = [
    path("", TargetCurrentView.as_view(), name="targets-current"),
    path("history/", TargetHistoryView.as_view(), name="targets-history"),
    path("suggest/", SuggestTargetView.as_view(), name="targets-suggest"),
    path("customize/", CustomizeTargetView.as_view(), name="targets-customize"),
    path("accept-suggestion/", AcceptSuggestionView.as_view(), name="targets-accept"),
]
