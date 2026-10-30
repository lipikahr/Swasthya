"""Scheduled Indian languages plus English. Original user text is never overwritten."""

import re

from django.conf import settings

SUPPORTED_LANGUAGES = (
    ("en", "English"),
    ("as", "Assamese"),
    ("bn", "Bengali"),
    ("brx", "Bodo"),
    ("doi", "Dogri"),
    ("gu", "Gujarati"),
    ("hi", "Hindi"),
    ("kn", "Kannada"),
    ("ks", "Kashmiri"),
    ("kok", "Konkani"),
    ("mai", "Maithili"),
    ("ml", "Malayalam"),
    ("mni", "Manipuri"),
    ("mr", "Marathi"),
    ("ne", "Nepali"),
    ("or", "Odia"),
    ("pa", "Punjabi"),
    ("sa", "Sanskrit"),
    ("sat", "Santali"),
    ("sd", "Sindhi"),
    ("ta", "Tamil"),
    ("te", "Telugu"),
    ("ur", "Urdu"),
)

SUPPORTED_CODES = {code for code, _name in SUPPORTED_LANGUAGES}

_SCRIPTS = (
    (re.compile(r"[\u0C80-\u0CFF]"), "kn"),
    (re.compile(r"[\u0B80-\u0BFF]"), "ta"),
    (re.compile(r"[\u0C00-\u0C7F]"), "te"),
    (re.compile(r"[\u0D00-\u0D7F]"), "ml"),
    (re.compile(r"[\u0A80-\u0AFF]"), "gu"),
    (re.compile(r"[\u0A00-\u0A7F]"), "pa"),
    (re.compile(r"[\u0980-\u09FF]"), "bn"),
    (re.compile(r"[\u0B00-\u0B7F]"), "or"),
    (re.compile(r"[\u0900-\u097F]"), "hi"),
    (re.compile(r"[\u0600-\u06FF]"), "ur"),
)


def detect_language(text: str, preferred: str | None = None) -> str:
    for pattern, code in _SCRIPTS:
        if pattern.search(text or ""):
            return code
    if preferred in SUPPORTED_CODES:
        return preferred
    return "en"


def working_text_for_model(text: str, language: str) -> tuple[str, str | None]:
    """Keep original user text. Translate only for internal model processing."""
    if language in {"", "en"} or not text:
        return text, None
    translated = _sarvam_translate(text, language, "en") or _openrouter_translate(text, "en", "English")
    if translated is None:
        return text, None
    return translated, translated


def localize_reply(text: str, language: str) -> str:
    if not text or language in {"", "en"}:
        return text
    name = dict(SUPPORTED_LANGUAGES).get(language, language)
    translated = _sarvam_translate(text, "en", language) or _openrouter_translate(text, language, name)
    if translated is None:
        return f"{text}\n\n(This reply could not be translated into {name}.)"
    return translated


_SARVAM_LANG = {
    "as": "as-IN",
    "bn": "bn-IN",
    "brx": "brx-IN",
    "doi": "doi-IN",
    "en": "en-IN",
    "gu": "gu-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
    "ks": "ks-IN",
    "kok": "gom-IN",
    "mai": "mai-IN",
    "ml": "ml-IN",
    "mni": "mni-IN",
    "mr": "mr-IN",
    "ne": "ne-IN",
    "or": "od-IN",
    "od": "od-IN",
    "pa": "pa-IN",
    "sa": "sa-IN",
    "sat": "sat-IN",
    "sd": "sd-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "ur": "ur-IN",
}


def bcp47_language(code: str | None) -> str | None:
    text = str(code or "").strip()
    if not text:
        return None
    if text in _SARVAM_LANG.values():
        return text
    return _SARVAM_LANG.get(text.casefold().split("-")[0])


def translate_for_search(text: str, language: str) -> str | None:
    """Translate a short food name for catalogue search. Never overwrites the user message."""
    cleaned = " ".join(str(text or "").split())
    if not cleaned or language in {"", "en"}:
        return None
    translated = _sarvam_translate(cleaned, language, "en")
    if translated:
        return translated
    return _openrouter_translate(cleaned, "en", "English")


def _sarvam_translate(text: str, source: str, target: str) -> str | None:
    key = str(getattr(settings, "SARVAM_API_KEY", "") or "").strip()
    source_code = _SARVAM_LANG.get(source)
    target_code = _SARVAM_LANG.get(target)
    if not key or not source_code or not target_code:
        return None
    import httpx

    try:
        response = httpx.post(
            "https://api.sarvam.ai/translate",
            headers={"api-subscription-key": key, "Content-Type": "application/json"},
            json={
                "input": text[:200],
                "source_language_code": source_code,
                "target_language_code": target_code,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload.get("translated_text") or payload.get("output") or "").strip() or None
    except Exception:
        return None


def _openrouter_translate(text: str, language: str, name: str) -> str | None:
    key = str(getattr(settings, "OPENROUTER_API_KEY", "") or "").strip()
    if not key:
        return None
    import httpx

    from .providers import configured_openrouter_model, openrouter_chat_url

    try:
        response = httpx.post(
            openrouter_chat_url(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": configured_openrouter_model(),
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            f"Translate into {name}. Keep numbers, units, meal categories, and food names unchanged. "
                            "Do not add foods or quantities. Reply with the translation only."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
            },
            timeout=20,
        )
        response.raise_for_status()
        return str(response.json()["choices"][0]["message"]["content"]).strip() or None
    except Exception:
        return None
