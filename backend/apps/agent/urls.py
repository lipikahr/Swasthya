from django.urls import path

from .views import ChatView, ImageView, VoiceView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="agent-chat"),
    path("voice/", VoiceView.as_view(), name="agent-voice"),
    path("image/", ImageView.as_view(), name="agent-image"),
]
