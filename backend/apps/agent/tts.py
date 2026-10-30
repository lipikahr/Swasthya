import logging
import re

import httpx
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError

logger = logging.getLogger(__name__)

SARVAM_TTS_DEFAULT = "https://api.sarvam.ai/text-to-speech"
_BCP47 = re.compile(r"^[a-z]{2,3}-[A-Z]{2}$")
# Documented Bulbul REST languages. This is not the full Eighth Schedule list.
TTS_LANGUAGE_CODES = {
    "bn": "bn-IN",
    "en": "en-IN",
    "gu": "gu-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "or": "od-IN",
    "od": "od-IN",
    "pa": "pa-IN",
    "ta": "ta-IN",
    "te": "te-IN",
}


def tts_language_code(language: str | None) -> str | None:
    text = str(language or "").strip()
    if _BCP47.match(text) and text in TTS_LANGUAGE_CODES.values():
        return text
    mapped = TTS_LANGUAGE_CODES.get(text.casefold().split("-")[0], "")
    return mapped or None


def speak_text(text: str, language: str | None = None) -> bytes:
    key = str(getattr(settings, "SARVAM_API_KEY", "") or "").strip()
    if not key:
        error = APIException("Listen is unavailable until SARVAM_API_KEY is configured.")
        error.status_code = 503
        error.default_code = "not_configured"
        raise error
    requested = str(language or "").strip()
    language_code = tts_language_code(requested) or ("en-IN" if requested in {"", "en", "en-IN"} else "")
    if not language_code:
        error = APIException("Spoken playback is not available for this language. The written reply is still available.")
        error.status_code = 422
        error.default_code = "spoken_unavailable"
        raise error
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        raise ValidationError({"text": ["There is no reply to read aloud."]})
    model = str(getattr(settings, "SARVAM_TTS_MODEL", "") or "bulbul:v3")
    payload = {
        "text": cleaned[:500],
        "target_language_code": language_code,
        "language_code": language_code,
        "model": model,
    }
    speaker = str(getattr(settings, "SARVAM_TTS_SPEAKER", "") or "").strip()
    if not speaker:
        speaker = "shubh" if model.startswith("bulbul:v3") else "anushka"
    payload["speaker"] = speaker
    try:
        response = httpx.post(
            str(getattr(settings, "SARVAM_TTS_URL", "") or SARVAM_TTS_DEFAULT),
            headers={"api-subscription-key": key, "Content-Type": "application/json"},
            json=payload,
            timeout=45,
        )
    except httpx.HTTPError as exc:
        logger.warning("sarvam tts failed exception=%s", type(exc).__name__)
        error = APIException("Listen is unavailable right now.")
        error.status_code = 503
        error.default_code = "provider"
        raise error from exc
    if response.status_code >= 400:
        logger.warning("sarvam tts http_code=%s", response.status_code)
        if response.status_code in {401, 403}:
            error = APIException("Listen credentials were rejected.")
            error.status_code = 403
            error.default_code = "invalid_credentials"
            raise error
        if response.status_code == 402:
            error = APIException("Listen has no remaining credits.")
            error.status_code = 402
            error.default_code = "insufficient_credits"
            raise error
        error = APIException("Listen is unavailable right now.")
        error.status_code = 502
        error.default_code = "provider"
        raise error
    if response.headers.get("content-type", "").startswith("audio"):
        return response.content
    try:
        body = response.json()
    except ValueError as exc:
        error = APIException("Listen is unavailable right now.")
        error.status_code = 502
        error.default_code = "provider"
        raise error from exc
    audio = body.get("audios") or body.get("audio")
    if isinstance(audio, list) and audio:
        import base64

        return base64.b64decode(audio[0])
    if isinstance(audio, str):
        import base64

        return base64.b64decode(audio)
    error = APIException("Listen is unavailable right now.")
    error.status_code = 502
    error.default_code = "provider"
    raise error
