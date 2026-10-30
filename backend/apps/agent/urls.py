from django.urls import path

from .views import ChatView, ConfirmMealView, DraftView, ImageView, SpeakView, TranscribeView, VoiceView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="agent-chat"),
    path("confirm/", ConfirmMealView.as_view(), name="agent-confirm"),
    path("draft/", DraftView.as_view(), name="agent-draft"),
    path("transcribe/", TranscribeView.as_view(), name="agent-transcribe"),
    path("voice/", VoiceView.as_view(), name="agent-voice"),
    path("image/", ImageView.as_view(), name="agent-image"),
    path("speak/", SpeakView.as_view(), name="agent-speak"),
]
