from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.models import Conversation, Message

from .workflow import run_text_turn


class ChatView(APIView):
    input_type = Message.InputType.TEXT

    def post(self, request):
        text = str(request.data.get("message") or request.data.get("transcript") or "").strip()
        if not text:
            raise ValidationError({"message": ["Tell me what you ate."]})
        return Response(_record_turn(request, text, self.input_type))


class VoiceView(APIView):
    """Device speech recognition sends a transcript. Raw audio is not transcribed here."""

    def post(self, request):
        if request.FILES.get("audio") and not str(request.data.get("transcript") or "").strip():
            error = APIException(
                "Upload audio is not transcribed on the server yet. Send the transcript from the device speech recognizer."
            )
            error.status_code = 501
            error.default_code = "not_available"
            raise error
        text = str(request.data.get("transcript") or "").strip()
        if not text:
            raise ValidationError({"transcript": ["A spoken transcript is required."]})
        return Response(_record_turn(request, text, Message.InputType.VOICE))


class ImageView(APIView):
    def post(self, request):
        error = APIException(
            "Image identification is not available until a vision provider is configured. An image will not be given an invented quantity."
        )
        error.status_code = 501
        error.default_code = "not_available"
        raise error


def _record_turn(request, text: str, input_type: str) -> dict:
    conversation_id = request.data.get("conversation_id")
    if conversation_id:
        conversation = get_object_or_404(Conversation.objects.filter(user=request.user), pk=conversation_id)
    else:
        conversation = Conversation.objects.create(user=request.user)
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=text,
        input_type=input_type,
    )
    result = run_text_turn(user_id=request.user.id, conversation_id=conversation.id, text=text)
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=result.get("reply") or "",
        input_type=Message.InputType.TEXT,
    )
    conversation.save(update_fields=["updated_at"])
    return {
        "status": result.get("status"),
        "conversation_id": conversation.id,
        "message": result.get("reply"),
        "meal_id": result.get("meal_id"),
        "provider": result.get("provider"),
    }
