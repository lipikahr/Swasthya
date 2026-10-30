"""Sarvam Saaras v4 transcription. Credentials stay on the server."""

import logging
import re

import httpx
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError

logger = logging.getLogger(__name__)

SARVAM_URL = "https://api.sarvam.ai/speech-to-text"
MAX_AUDIO_BYTES = 8 * 1024 * 1024
_BCP47 = re.compile(r"^[a-z]{2,3}-[A-Z]{2}$")


def sarvam_configuration() -> dict:
    """Safe operator status. Never includes the API key."""
    return {
        "key_configured": bool(str(getattr(settings, "SARVAM_API_KEY", "") or "").strip()),
        "stt_model": str(getattr(settings, "SARVAM_STT_MODEL", "") or "saaras:v4"),
        "stt_mode": str(getattr(settings, "SARVAM_STT_MODE", "") or "transcribe"),
        "tts_model": str(getattr(settings, "SARVAM_TTS_MODEL", "") or "bulbul:v3"),
    }


def transcribe_audio(upload, *, language: str | None = None, keyterms: list[str] | None = None) -> dict:
    key = str(getattr(settings, "SARVAM_API_KEY", "") or "").strip()
    if not key:
        error = APIException(
            "Voice transcription is not configured. Add SARVAM_API_KEY to the root .env, or type the meal instead."
        )
        error.status_code = 503
        error.default_code = "not_configured"
        raise error
    if upload is None:
        raise ValidationError({"audio": ["Record audio before sending it for transcription."]})
    data = upload.read()
    if not data:
        raise ValidationError({"audio": ["The recording was empty."]})
    if len(data) > MAX_AUDIO_BYTES:
        raise ValidationError({"audio": ["The recording is too large. Stop sooner and try again."]})
    filename = getattr(upload, "name", "speech.webm") or "speech.webm"
    content_type = getattr(upload, "content_type", None) or "audio/webm"
    fields = {
        "model": (None, str(getattr(settings, "SARVAM_STT_MODEL", "") or "saaras:v4")),
        "mode": (None, str(getattr(settings, "SARVAM_STT_MODE", "") or "transcribe")),
        "file": (filename, data, content_type),
    }
    hint = _stt_language_hint(language)
    if hint:
        fields["language_code"] = (None, hint)
    try:
        response = httpx.post(
            str(getattr(settings, "SARVAM_STT_URL", "") or SARVAM_URL),
            headers={"api-subscription-key": key},
            files=fields,
            timeout=30,
        )
    except httpx.HTTPError as exc:
        logger.warning("sarvam transcription failed exception=%s", type(exc).__name__)
        error = APIException("Voice transcription could not be reached. Type the meal instead.")
        error.status_code = 503
        error.default_code = "provider"
        raise error from exc
    if response.status_code >= 400:
        status_code, code, message = _classify_stt_error(response)
        logger.warning("sarvam transcription http_code=%s error_code=%s", response.status_code, code)
        error = APIException(message)
        error.status_code = status_code
        error.default_code = code
        raise error
    payload = response.json()
    transcript = str(payload.get("transcript") or payload.get("text") or "").strip()
    if not transcript:
        raise ValidationError({"audio": ["No speech was recognized. Try again or type the meal."]})
    detected = payload.get("language_code") or payload.get("language") or language
    return {
        "transcript": transcript,
        "language": detected,
        "submitted": False,
    }


def _stt_language_hint(language: str | None) -> str | None:
    """Saaras auto-detects by default. An explicit Voice setting is sent as BCP-47, never kn."""
    from .languages import bcp47_language

    text = str(language or "").strip()
    if not text or text in {"en", "en-IN"}:
        return None
    if _BCP47.match(text):
        return text
    return bcp47_language(text)


def _classify_stt_error(response) -> tuple[int, str, str]:
    folded = ""
    try:
        payload = response.json()
        folded = str(payload.get("error") or payload.get("message") or payload).casefold()
    except ValueError:
        folded = (response.text or "").casefold()[:240]
    status = response.status_code
    if status in {401, 403}:
        return 403, "invalid_credentials", "Voice transcription credentials were rejected. Type the meal instead."
    if status == 402 or "credit" in folded or "quota" in folded or "insufficient" in folded:
        return 402, "insufficient_credits", "Voice transcription has no remaining credits. Type the meal instead."
    if status in {415, 422} or "unsupported" in folded:
        return 400, "unsupported_audio", "That recording could not be transcribed. Try again or type the meal."
    if status == 400:
        return 400, "unsupported_audio", "That recording could not be transcribed. Try again or type the meal."
    return 502, "provider", "Voice transcription failed. Type the meal instead."
