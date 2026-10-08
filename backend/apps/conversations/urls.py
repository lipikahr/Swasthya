from django.urls import path

from .views import ConversationDetailView, ConversationListView

urlpatterns = [
    path("", ConversationListView.as_view(), name="conversations"),
    path("<int:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
]
