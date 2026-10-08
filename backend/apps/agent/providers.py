"""Turn user text into food mentions.

The rules provider covers clear sentences such as "I ate 2 idlis for breakfast"
when no Gemini key is configured. It does not invent nutrition values.
Gemini, when configured, must return the same shape. A user id in the model
output is ignored.
"""

import json
import re

from django.conf import settings

MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}
UNIT_PATTERN = r"kilograms|kilogram|grams|gram|kg|g"
PART_PATTERN = re.compile(
    rf"^(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>{UNIT_PATTERN})?\s*(?:of\s+)?(?P<food>.+)$",
    re.IGNORECASE,
)


class ProviderError(Exception):
    pass


class RulesProvider:
    name = "rules"

    def extract(self, text: str) -> dict:
        cleaned = " ".join(text.strip().split())
        meal_type = None
        meal_match = re.search(r"\bfor\s+(breakfast|lunch|dinner|snack)\b", cleaned, re.IGNORECASE)
        if meal_match:
            meal_type = meal_match.group(1).lower()
            cleaned = f"{cleaned[: meal_match.start()]} {cleaned[meal_match.end():]}"
            cleaned = " ".join(cleaned.split())
        cleaned = re.sub(
            r"^(?:i\s+)?(?:just\s+)?(?:have\s+eaten|ate|had|eaten)\s+",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip(" .")
        if not cleaned:
            return {"provider": self.name, "meal_type": meal_type, "items": []}
        items = [_parse_part(part.strip(" .")) for part in re.split(r"\s+and\s+", cleaned, flags=re.IGNORECASE)]
        return {"provider": self.name, "meal_type": meal_type, "items": [item for item in items if item["food_query"]]}


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def extract(self, text: str) -> dict:
        from google import genai

        prompt = (
            "Extract meal items from the user text. Reply with JSON only, "
            'shaped as {"meal_type": "breakfast"|"lunch"|"dinner"|"snack"|null, '
            '"items": [{"food_query": string, "quantity": number|null, "unit": string|null}]}. '
            "Do not include a user id. Do not invent nutrition numbers.\n\n"
            f"User text: {text}"
        )
        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            payload = json.loads(response.text or "")
        except Exception as exc:
            raise ProviderError("The language model could not read that message.") from exc
        meal_type = payload.get("meal_type")
        if meal_type not in MEAL_TYPES:
            meal_type = None
        items = []
        for raw in payload.get("items") or []:
            if not isinstance(raw, dict):
                continue
            query = str(raw.get("food_query") or "").strip()
            if not query:
                continue
            items.append({"food_query": query, "quantity": raw.get("quantity"), "unit": raw.get("unit")})
        return {"provider": self.name, "meal_type": meal_type, "items": items}


def get_provider():
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    if api_key.strip():
        return GeminiProvider(api_key=api_key.strip(), model=settings.GEMINI_MODEL)
    return RulesProvider()


def _parse_part(part: str) -> dict:
    match = PART_PATTERN.match(part)
    if match is None:
        return {"food_query": part, "quantity": None, "unit": None}
    unit = match.group("unit")
    return {
        "food_query": match.group("food").strip(),
        "quantity": match.group("qty"),
        "unit": None if unit is None else unit.lower(),
    }
