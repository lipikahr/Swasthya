import logging
import re
import threading
from collections import defaultdict

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.models import Conversation, Message

from django.http import HttpResponse

from apps.profiles.models import UserProfile

from .speech import transcribe_audio
from .tts import speak_text
from .vision import identify_food_candidates
from .workflow import cancel_pending_meal, confirm_pending_meal, pending_confirmation, run_text_turn, update_pending_meal

logger = logging.getLogger(__name__)
_TURN_LOCKS: dict[int, threading.Lock] = defaultdict(threading.Lock)
_INFLIGHT: dict[int, dict] = {}
_INFLIGHT_GUARD = threading.Lock()


class ChatView(APIView):
    input_type = Message.InputType.TEXT

    def post(self, request):
        text = str(request.data.get("message") or request.data.get("transcript") or "").strip()
        if not text:
            raise ValidationError({"message": ["Tell me what you ate."]})
        return Response(_record_turn(request, text, self.input_type))


class TranscribeView(APIView):
    """Speech-to-text only. The transcript is not a meal and is not submitted."""

    def post(self, request):
        language = str(request.data.get("language") or "").strip() or _profile_language(request.user)
        result = transcribe_audio(request.FILES.get("audio"), language=language)
        return Response(result)


class VoiceView(APIView):
    """Optional: a reviewed transcript can be sent as a chat turn. Audio is transcribed separately."""

    def post(self, request):
        if request.FILES.get("audio") and not str(request.data.get("transcript") or "").strip():
            language = str(request.data.get("language") or "").strip() or _profile_language(request.user)
            result = transcribe_audio(request.FILES.get("audio"), language=language)
            return Response(result)
        text = str(request.data.get("transcript") or "").strip()
        if not text:
            raise ValidationError({"transcript": ["A spoken transcript is required."]})
        return Response(_record_turn(request, text, Message.InputType.VOICE))


class ImageView(APIView):
    def post(self, request):
        result = identify_food_candidates(request.FILES.get("image") or request.FILES.get("photo"))
        return Response(result)


class SpeakView(APIView):
    def post(self, request):
        language = str(request.data.get("language") or "").strip() or _profile_language(request.user)
        audio = speak_text(str(request.data.get("text") or ""), language=language)
        return HttpResponse(audio, content_type="audio/mpeg")


def _profile_language(user) -> str | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    profile = UserProfile.objects.filter(user=user).first()
    return getattr(profile, "preferred_language", None) or None


def join_or_run_turn(conversation_id: int, text: str, run):
    """Reuse an in-flight turn for the same conversation and text.

    A refresh or second Send while Gemini is still running used to persist the
    user message twice. Waiters receive the owner's result instead of starting
    another extract.
    """
    with _INFLIGHT_GUARD:
        current = _INFLIGHT.get(conversation_id)
        if current is not None and current["text"] == text:
            slot = current
            owner = False
        else:
            slot = {"text": text, "event": threading.Event(), "result": None, "error": None}
            _INFLIGHT[conversation_id] = slot
            owner = True
    if not owner:
        slot["event"].wait(timeout=180)
        if slot["error"] is not None:
            raise slot["error"]
        if slot["result"] is not None:
            return slot["result"]
        error = APIException("The previous request is still running. Try again shortly.")
        error.status_code = 409
        error.default_code = "turn_in_progress"
        raise error
    try:
        with _TURN_LOCKS[conversation_id]:
            result = run()
        slot["result"] = result
        return result
    except Exception as exc:
        slot["error"] = exc
        raise
    finally:
        slot["event"].set()
        with _INFLIGHT_GUARD:
            if _INFLIGHT.get(conversation_id) is slot:
                del _INFLIGHT[conversation_id]


def _execute_turn(user, conversation: Conversation, text: str, input_type: str) -> dict:
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=text,
        input_type=input_type,
    )
    try:
        result = run_text_turn(user_id=user.id, conversation_id=conversation.id, text=text)
    except Exception as exc:
        detail = re.sub(r"(?i)sk-[A-Za-z0-9_\-]{8,}", "[redacted]", str(exc))
        detail = re.sub(r"(?i)bearer\s+\S+", "Bearer [redacted]", detail)
        logger.warning("chat turn failed exception=%s detail=%s", type(exc).__name__, detail[:240])
        result = {
            "status": "ERROR",
            "reply": "We couldn't process your request. Please try again.",
            "meal_id": None,
            "provider": None,
            "reason": "server",
        }
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=result.get("reply") or "",
        input_type=Message.InputType.TEXT,
    )
    conversation.save(update_fields=["updated_at"])
    body = {
        "status": result.get("status"),
        "conversation_id": conversation.id,
        "message": result.get("reply"),
        "meal_id": result.get("meal_id"),
        "provider": result.get("provider"),
    }
    if result.get("reason"):
        body["reason"] = result["reason"]
    if result.get("confirmation") is not None:
        body["confirmation"] = result["confirmation"]
    if result.get("suggestions") is not None:
        body["suggestions"] = result["suggestions"]
    if result.get("allergy_note"):
        body["allergy_note"] = result["allergy_note"]
    body["original_text"] = text
    if result.get("language"):
        body["language"] = result["language"]
    return body


def _owned_conversation(request) -> Conversation:
    conversation_id = request.data.get("conversation_id") or request.query_params.get("conversation_id")
    if not conversation_id:
        raise ValidationError({"conversation_id": ["Choose the conversation for this meal."]})
    return get_object_or_404(Conversation.objects.filter(user=request.user), pk=conversation_id)


class ConfirmMealView(APIView):
    def post(self, request):
        conversation = _owned_conversation(request)
        return Response(
            confirm_pending_meal(
                user=request.user,
                conversation=conversation,
                meal_type=request.data.get("meal_type"),
            )
        )


class DraftView(APIView):
    def get(self, request):
        conversation = _owned_conversation(request)
        return Response(pending_confirmation(user=request.user, conversation=conversation))

    def post(self, request):
        conversation = _owned_conversation(request)
        action = str(request.data.get("action") or "").strip().lower()
        if action == "cancel":
            return Response(cancel_pending_meal(user=request.user, conversation=conversation))
        if action == "edit":
            return Response(
                update_pending_meal(
                    user=request.user,
                    conversation=conversation,
                    meal_type=request.data.get("meal_type") if "meal_type" in request.data else None,
                    items=request.data.get("items") if "items" in request.data else None,
                )
            )
        raise ValidationError({"action": ["Choose edit or cancel."]})


def _record_turn(request, text: str, input_type: str) -> dict:
    conversation_id = request.data.get("conversation_id")
    if conversation_id:
        conversation = get_object_or_404(Conversation.objects.filter(user=request.user), pk=conversation_id)
    else:
        conversation = Conversation.objects.create(user=request.user)
    return join_or_run_turn(
        conversation.id,
        text,
        lambda: _execute_turn(request.user, conversation, text, input_type),
    )
