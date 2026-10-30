"""Turn user text into food mentions.

The rules provider covers clear sentences such as "I ate 2 idlis for breakfast"
when no Gemini key is configured. It does not invent nutrition values.
Gemini, when configured, must return the same shape. A user id in the model
output is ignored.
"""

import json
import logging
import re
import time

from django.conf import settings

logger = logging.getLogger(__name__)

EXTRACT_ATTEMPTS = 4
EXTRACT_TIMEOUT_MS = 90_000
EXTRACT_RETRY_REASONS = {"unavailable", "timeout", "network"}
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}


class ProviderError(Exception):
    def __init__(self, message: str, reason: str = "provider", details: dict | None = None):
        super().__init__(message)
        self.reason = reason
        self.details = details or {}


class RulesProvider:
    name = "rules"

    def extract(self, text: str) -> dict:
        from .extract import extract_mentions

        extracted = extract_mentions(text)
        return {
            "provider": self.name,
            "meal_type": extracted.get("meal_type"),
            "items": extracted.get("items") or [],
        }


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        from google import genai
        from google.genai import types

        self.model = model or "models/gemini-3.8-flash"
        # SDK retries default to off (retry_options=None). This method retries
        # unavailable/timeout/network itself so Django logs show each attempt
        # and a 120s client timeout cannot stack into a multi-minute hang.
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=EXTRACT_TIMEOUT_MS),
        )
        self._generate_config = types.GenerateContentConfig(response_mime_type="application/json")

    def extract(self, text: str) -> dict:
        prompt = _meal_extract_prompt(text)
        last_error: ProviderError | None = None
        for attempt in range(1, EXTRACT_ATTEMPTS + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=self._generate_config,
                )
                payload = json.loads(response.text or "")
                break
            except Exception as exc:
                details = describe_gemini_exception(exc)
                last_error = ProviderError(details["message"], reason=details["reason"], details=details)
                last_error.__cause__ = exc
                logger.warning(
                    "Gemini extract failed attempt=%s/%s reason=%s exception=%s http_code=%s status=%s model=%s",
                    attempt,
                    EXTRACT_ATTEMPTS,
                    details["reason"],
                    details["exception"],
                    details["http_code"],
                    details["status"],
                    self.model,
                )
                if details["reason"] not in EXTRACT_RETRY_REASONS or attempt >= EXTRACT_ATTEMPTS:
                    raise last_error from exc
                time.sleep(_extract_retry_delay(details["reason"], attempt))
        else:
            raise last_error or ProviderError("The language model could not be reached.", reason="provider")
        return _extract_payload(self.name, payload)


class OpenRouterProvider:
    name = "openrouter"

    def __init__(self, api_key: str, model: str):
        self.model = model or "openai/gpt-4o-mini"
        self._api_key = api_key
        self._url = openrouter_chat_url()
        self._referer = str(getattr(settings, "OPENROUTER_HTTP_REFERER", "") or "").strip()
        self._title = str(getattr(settings, "OPENROUTER_APP_TITLE", "") or "").strip() or "Swasthya"

    def extract(self, text: str) -> dict:
        import httpx

        prompt = _meal_extract_prompt(text)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._referer:
            headers["HTTP-Referer"] = self._referer
        if self._title:
            headers["X-Title"] = self._title
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }
        last_error: ProviderError | None = None
        for attempt in range(1, EXTRACT_ATTEMPTS + 1):
            try:
                response = httpx.post(
                    self._url,
                    headers=headers,
                    json=body,
                    timeout=EXTRACT_TIMEOUT_MS / 1000,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                payload = json.loads(content or "")
                break
            except Exception as exc:
                details = describe_openrouter_exception(exc)
                last_error = ProviderError(details["message"], reason=details["reason"], details=details)
                last_error.__cause__ = exc
                logger.warning(
                    "OpenRouter extract failed attempt=%s/%s reason=%s exception=%s http_code=%s status=%s model=%s upstream=%s",
                    attempt,
                    EXTRACT_ATTEMPTS,
                    details["reason"],
                    details["exception"],
                    details["http_code"],
                    details["status"],
                    self.model,
                    details.get("upstream") or "",
                )
                if details["reason"] not in EXTRACT_RETRY_REASONS or attempt >= EXTRACT_ATTEMPTS:
                    raise last_error from exc
                time.sleep(_extract_retry_delay(details["reason"], attempt))
        else:
            raise last_error or ProviderError("The language model could not be reached.", reason="provider")
        return _extract_payload(self.name, payload)


def _meal_extract_prompt(text: str) -> str:
    return (
        "Extract meal items from the user text. Reply with JSON only, "
        'shaped as {"meal_type": "breakfast"|"lunch"|"dinner"|"snack"|null, '
        '"items": [{"food_query": string, "quantity": number|null, "unit": string|null}]}. '
        "food_query must be only the food name, such as chapati, milk, or upma. "
        "Do not put the whole sentence, the quantity, or phrases such as \"I ate\" in food_query. "
        "quantity must be a number using 0-9 digits. unit must be a short string such as g, kg, piece, or idli. "
        "Do not include a user id. Do not invent nutrition numbers.\n\n"
        f"User text: {text}"
    )


def _extract_payload(provider: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        logger.warning("extract payload rejected provider=%s reason=not_object", provider)
        return {"provider": provider, "meal_type": None, "items": []}
    meal_type = payload.get("meal_type")
    if meal_type not in MEAL_TYPES:
        meal_type = None
    items = []
    raw_items = payload.get("items")
    if raw_items is None:
        raw_items = []
    if not isinstance(raw_items, list):
        logger.warning("extract payload rejected provider=%s reason=items_not_list", provider)
        return {"provider": provider, "meal_type": meal_type, "items": []}
    for raw in raw_items:
        if not isinstance(raw, dict):
            logger.warning("extract item skipped provider=%s reason=item_not_object", provider)
            continue
        query = raw.get("food_query")
        if isinstance(query, (dict, list)):
            logger.warning("extract item skipped provider=%s reason=food_query_malformed", provider)
            continue
        quantity = raw.get("quantity")
        unit = raw.get("unit")
        if isinstance(quantity, (dict, list, bool)):
            logger.warning("extract item skipped provider=%s reason=quantity_malformed", provider)
            continue
        if isinstance(unit, (dict, list)):
            logger.warning("extract item skipped provider=%s reason=unit_malformed", provider)
            continue
        query, quantity, unit = normalize_mention(str(query or ""), quantity, unit)
        if not query:
            continue
        original = str(raw.get("original_query") or query).strip()
        items.append({"food_query": query, "quantity": quantity, "unit": unit, "original_query": original})
    return {"provider": provider, "meal_type": meal_type, "items": items}


def _sanitize_upstream_message(message: str) -> str:
    """Keep a provider error safe for logs. Drops credentials and any echoed user text."""
    text = str(message or "")
    text = re.sub(r"(?i)sk-[A-Za-z0-9_\-]{8,}", "[redacted]", text)
    text = re.sub(r"(?i)bearer\s+\S+", "Bearer [redacted]", text)
    text = re.split(r"(?i)user text:", text, maxsplit=1)[0]
    text = re.sub(r"\s+", " ", text).strip()
    return text[:240]


def _strip_env_value(raw: str) -> str:
    value = str(raw or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1].strip()
    return value


def _configured_openrouter_key() -> str:
    return _strip_env_value(getattr(settings, "OPENROUTER_API_KEY", ""))


def configured_openrouter_model() -> str:
    return _strip_env_value(getattr(settings, "OPENROUTER_MODEL", "")) or "openai/gpt-4o-mini"


def configured_openrouter_base_url() -> str:
    return _strip_env_value(getattr(settings, "OPENROUTER_BASE_URL", "")) or DEFAULT_OPENROUTER_BASE_URL


def openrouter_chat_url() -> str:
    return f"{configured_openrouter_base_url().rstrip('/')}/chat/completions"


def _configured_gemini_key() -> str:
    return _strip_env_value(getattr(settings, "GEMINI_API_KEY", ""))


def configured_gemini_model() -> str:
    return str(getattr(settings, "GEMINI_MODEL", "") or "").strip() or "models/gemini-3.8-flash"


def gemini_configuration() -> dict:
    """Safe status for operators. Never includes API keys."""
    openrouter_key = _configured_openrouter_key()
    if openrouter_key:
        return {
            "key_configured": True,
            "provider": "openrouter",
            "model": configured_openrouter_model(),
            "base_url": configured_openrouter_base_url(),
        }
    gemini_key = _configured_gemini_key()
    return {
        "key_configured": bool(gemini_key),
        "provider": "gemini" if gemini_key else "rules",
        "model": configured_gemini_model(),
    }


def get_provider():
    openrouter_key = _configured_openrouter_key()
    if openrouter_key:
        return OpenRouterProvider(api_key=openrouter_key, model=configured_openrouter_model())
    api_key = _configured_gemini_key()
    if api_key:
        return GeminiProvider(api_key=api_key, model=configured_gemini_model())
    return RulesProvider()


def describe_openrouter_exception(exc: BaseException) -> dict:
    import httpx

    details = {
        "exception": type(exc).__name__,
        "http_code": None,
        "status": None,
        "reason": "provider",
        "message": "The language model could not read that message.",
    }
    if isinstance(exc, httpx.HTTPStatusError):
        details["http_code"] = exc.response.status_code
        hint = ""
        try:
            payload = exc.response.json()
            err = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(err, dict):
                details["status"] = str(err.get("code") or err.get("type") or "")
                details["upstream"] = _sanitize_upstream_message(str(err.get("message") or ""))
                hint = str(err.get("message") or "").lower()
            else:
                details["upstream"] = _sanitize_upstream_message(str(err or ""))
                hint = str(payload).lower()
        except Exception:
            details["upstream"] = ""
        code = int(details["http_code"] or 0)
        if code in {401, 403} or "invalid" in hint and "key" in hint:
            details["reason"] = "credentials"
            details["message"] = "The language model rejected the configured credentials."
            return details
        if code == 429:
            details["reason"] = "rate_limit"
            details["message"] = "The language model is rate limited. Try again shortly."
            return details
        if code in {408, 504}:
            details["reason"] = "timeout"
            details["message"] = "The language model took too long to respond. Try again shortly."
            return details
        if code >= 500:
            details["reason"] = "unavailable"
            details["message"] = "The language model is temporarily unavailable. Try again shortly."
            return details
        if code == 404:
            details["reason"] = "model"
            details["message"] = "The configured model was not found."
            return details
        return details
    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException)):
        details["reason"] = "timeout"
        details["message"] = "The language model took too long to respond. Try again shortly."
        return details
    if isinstance(exc, (httpx.ConnectError, httpx.NetworkError)):
        details["reason"] = "network"
        details["message"] = "The language model could not be reached."
        return details
    if isinstance(exc, (json.JSONDecodeError, KeyError, IndexError, TypeError)):
        details["reason"] = "provider"
        details["message"] = "The language model returned an unexpected response."
        return details
    return details


def describe_gemini_exception(exc: BaseException) -> dict:
    import httpx
    from google.genai import errors

    details = {
        "exception": type(exc).__name__,
        "http_code": getattr(exc, "code", None),
        "status": getattr(exc, "status", None),
        "reason": "provider",
        "message": "The language model could not read that message.",
    }
    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException)):
        details["reason"] = "timeout"
        details["message"] = "The language model took too long to respond. Try again shortly."
        return details
    if isinstance(exc, (httpx.ConnectError, httpx.NetworkError)):
        details["reason"] = "network"
        details["message"] = "The language model could not be reached."
        return details
    if isinstance(exc, errors.APIError):
        code = int(exc.code or 0)
        status = str(exc.status or "").upper()
        hint = str(exc.message or "").lower()
        details["http_code"] = code
        details["status"] = status
        if code in {401, 403} or status in {"UNAUTHENTICATED", "PERMISSION_DENIED"}:
            details["reason"] = "credentials"
            details["message"] = "The language model rejected the configured credentials."
            return details
        if "api key" in hint or "api_key" in hint or "credential" in hint:
            details["reason"] = "credentials"
            details["message"] = "The language model rejected the configured credentials."
            return details
        if code == 429 or status == "RESOURCE_EXHAUSTED":
            details["reason"] = "rate_limit"
            details["message"] = "The language model is rate limited. Try again shortly."
            return details
        if code == 504 or status in {"DEADLINE_EXCEEDED", "GATEWAY_TIMEOUT"}:
            details["reason"] = "timeout"
            details["message"] = "The language model took too long to respond. Try again shortly."
            return details
        if isinstance(exc, errors.ServerError) or code >= 500 or status in {"UNAVAILABLE", "INTERNAL"}:
            details["reason"] = "unavailable"
            details["message"] = "The language model is temporarily unavailable. Try again shortly."
            return details
        if code == 404 or status == "NOT_FOUND":
            details["reason"] = "model"
            details["message"] = "The configured Gemini model was not found."
            return details
    return details


def classify_gemini_exception(exc: BaseException) -> tuple[str, str]:
    details = describe_gemini_exception(exc)
    return details["reason"], details["message"]


def probe_gemini() -> dict:
    """Attempt one real Gemini extract. Reports error classes without secret values."""
    status = gemini_configuration()
    result = {
        "key_configured": status["key_configured"],
        "provider": status["provider"],
        "model": status["model"],
        "ok": False,
        "live_request": "not_attempted",
        "error_class": None,
        "message": None,
    }
    if not status["key_configured"]:
        result["error_class"] = "configuration"
        result["message"] = "No OPENROUTER_API_KEY or GEMINI_API_KEY is configured in the root .env."
        return result
    try:
        extracted = get_provider().extract("I ate 1 idli for breakfast")
    except ProviderError as exc:
        result["live_request"] = "failed"
        result["error_class"] = getattr(exc, "reason", "provider")
        result["message"] = str(exc)
        return result
    result["ok"] = True
    result["live_request"] = "succeeded"
    result["extracted_item_count"] = len(extracted.get("items") or [])
    result["extracted_provider"] = extracted.get("provider")
    return result


def _extract_retry_delay(reason: str, attempt: int) -> float:
    if reason == "rate_limit":
        return min(20.0, 8.0 * attempt)
    return min(8.0, 2 ** (attempt - 1))


_QUANTITY_WORDS = {
    "a": "1",
    "an": "1",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
}
_WEIGHT_REPLY = re.compile(
    r"(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>kilograms|kilogram|grams|gram|kgs|kg|g)\b",
    re.IGNORECASE,
)
_COUNT_REPLY = re.compile(
    r"\b(?P<qty>\d+(?:\.\d+)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?P<unit>[A-Za-z]+)\b",
    re.IGNORECASE,
)
_QUANTITY_FILLER = {"about", "around", "approximately", "approx", "roughly", "of", "for", "the"}


_SCRIPT_UNITS = (
    (re.compile(r"ಗ್ರಾಂ|ग्राम|கிராம்|గ్రాములు|గ్రాము|গ্রাম", re.I), "g"),
    (re.compile(r"ಕೆಜಿ|किलो|किलोग्राम|கிலோ", re.I), "kg"),
)


def parse_quantity_reply(text: str) -> dict | None:
    """Read a quantity from a follow-up reply.

    An explicit weight wins, so "1 plate about 350g" is 350 g. A plate, bowl,
    or piece is returned as that unit and is not converted into grams.
    """
    from apps.nutrition.normalize import fold_digits

    from .extract import _QUANTITY_WORDS as INDIC_QUANTITY

    cleaned = fold_digits(text or "")
    for pattern, unit in _SCRIPT_UNITS:
        cleaned = pattern.sub(f" {unit} ", cleaned)
    cleaned = " ".join(cleaned.split())
    weight = _WEIGHT_REPLY.search(cleaned)
    if weight is not None:
        unit = weight.group("unit").lower()
        if unit in {"g", "gram", "grams"}:
            unit = "g"
        elif unit in {"kg", "kgs", "kilogram", "kilograms"}:
            unit = "kg"
        return {"quantity": weight.group("qty"), "unit": unit}
    count = _COUNT_REPLY.search(cleaned)
    if count is not None:
        unit = count.group("unit").lower()
        if unit not in _QUANTITY_FILLER and unit not in {"g", "gram", "grams", "kg", "kgs", "kilogram", "kilograms"}:
            raw = count.group("qty").lower()
            quantity = _QUANTITY_WORDS.get(raw, raw)
            return {"quantity": quantity, "unit": unit}
    stripped = cleaned.strip(" .!?।")
    folded = stripped.casefold()
    if folded in _QUANTITY_WORDS:
        return {"quantity": _QUANTITY_WORDS[folded], "unit": None}
    if stripped in INDIC_QUANTITY:
        return {"quantity": INDIC_QUANTITY[stripped], "unit": None}
    if re.fullmatch(r"\d+(?:\.\d+)?", stripped):
        return {"quantity": stripped, "unit": None}
    return None


_CONVERSATION_PREFIX = re.compile(
    r"^(?:(?:please|can you|could you|would you)\s+)*(?:(?:log|record|add|track)\s+)?"
    r"(?:(?:i|we)\s+)?(?:just\s+)?(?:have\s+eaten|have\s+had|ate|had|eaten|consumed|drank|drunk|have)\s+",
    re.IGNORECASE,
)
_MEAL_PHRASE = re.compile(r"\b(?:for|as)\s+(?:a\s+|an\s+)?(?:breakfast|lunch|dinner|snack)\b", re.IGNORECASE)
_LEADING_PORTION = re.compile(
    r"^(?:(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?)\s+)?"
    r"(?:plates|plate|bowls|bowl|glasses|glass|cups|cup|spoons|spoon|pieces|piece|servings|serving)\s+(?:of\s+)?",
    re.IGNORECASE,
)
_LEADING_AMOUNT = re.compile(
    r"^(?P<qty>\d+(?:\.\d+)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
    r"(?:(?P<unit>kilograms|kilogram|grams|gram|kgs|kg|g|plates|plate|bowls|bowl|glasses|glass|cups|cup|spoons|spoon|pieces|piece|servings|serving)\s+)?"
    r"(?:of\s+)?",
    re.IGNORECASE,
)
_WEIGHT_UNITS = {"g": "g", "gram": "g", "grams": "g", "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg"}


def clean_food_query(query: str) -> str:
    """Leave the food name. Drop the sentence, meal phrase, and leading amount."""
    text = " ".join(str(query or "").strip().split())
    previous = None
    while text and text != previous:
        previous = text
        text = _MEAL_PHRASE.sub(" ", text)
        text = " ".join(text.split()).strip(" .,")
        text = _CONVERSATION_PREFIX.sub("", text).strip(" .,")
        text = _LEADING_PORTION.sub("", text).strip(" .,")
        amount = _LEADING_AMOUNT.match(text)
        if amount is not None:
            text = text[amount.end() :].strip(" .,")
        text = re.sub(r"^of\s+", "", text, flags=re.IGNORECASE).strip(" .,")
    return " ".join(text.split()).strip(" .")


def normalize_mention(query: str, quantity=None, unit=None) -> tuple[str, str | None, str | None]:
    """Split a conversational mention into a food name, quantity, and unit.

    A model that returns the whole sentence as food_query is reduced to the
    food name before any dataset search. Household units are not converted
    into grams.
    """
    text = " ".join(str(query or "").strip().split())
    text = _MEAL_PHRASE.sub(" ", text)
    text = " ".join(text.split()).strip(" .,")
    text = _CONVERSATION_PREFIX.sub("", text).strip(" .,")
    amount = _LEADING_AMOUNT.match(text)
    parsed_quantity = None
    parsed_unit = None
    if amount is not None:
        parsed_quantity = _QUANTITY_WORDS.get(amount.group("qty").lower(), amount.group("qty"))
        if amount.group("unit"):
            raw_unit = amount.group("unit").lower()
            parsed_unit = _WEIGHT_UNITS.get(raw_unit, raw_unit)
    if quantity in (None, ""):
        quantity = parsed_quantity
    if unit in (None, "") and parsed_unit:
        unit = parsed_unit
    food = clean_food_query(query)
    return (
        food,
        None if quantity in (None, "") else str(quantity),
        None if unit in (None, "") else str(unit).lower(),
    )


def _parse_part(part: str) -> dict:
    query, quantity, unit = normalize_mention(part)
    return {"food_query": query, "quantity": quantity, "unit": unit}
