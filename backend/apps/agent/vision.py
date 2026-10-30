import base64
import json
import logging
import re

import httpx
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 4 * 1024 * 1024


def identify_food_candidates(upload) -> dict:
    if upload is None:
        raise ValidationError({"image": ["Choose a photo of the food."]})
    content_type = getattr(upload, "content_type", "") or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise ValidationError({"image": ["Use a JPEG, PNG, or WebP photo."]})
    data = upload.read()
    if not data:
        raise ValidationError({"image": ["The photo was empty."]})
    if len(data) > MAX_IMAGE_BYTES:
        raise ValidationError({"image": ["The photo is too large."]})
    key = str(getattr(settings, "OPENROUTER_API_KEY", "") or "").strip()
    if not key:
        error = APIException("Image identification is not configured. Type the food name instead.")
        error.status_code = 503
        error.default_code = "not_configured"
        raise error
    encoded = base64.b64encode(data).decode("ascii")
    url = f"data:{content_type};base64,{encoded}"
    payload = {
        "model": str(getattr(settings, "OPENROUTER_MODEL", "") or "openai/gpt-4o-mini"),
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": 'Name candidate foods in this photo. Reply JSON {"candidates":["name"]}. Names only. No calories.',
                    },
                    {"type": "image_url", "image_url": {"url": url}},
                ],
            }
        ],
        "temperature": 0,
    }
    try:
        response = httpx.post(
            f"{str(getattr(settings, 'OPENROUTER_BASE_URL', '') or 'https://openrouter.ai/api/v1').rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )
    except httpx.HTTPError as exc:
        logger.warning("vision request failed exception=%s", type(exc).__name__)
        error = APIException("The photo could not be identified. Type the food instead.")
        error.status_code = 503
        error.default_code = "provider"
        raise error from exc
    if response.status_code >= 400:
        logger.warning("vision http_code=%s", response.status_code)
        error = APIException("The photo could not be identified. Type the food instead.")
        error.status_code = 502
        error.default_code = "provider"
        raise error
    body = response.json()
    text = ""
    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        text = ""
    names = _parse_names(text)
    return {"candidates": names, "kcal_from_image": False}


def _parse_names(text: str) -> list[str]:
    raw = text.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            items = parsed.get("candidates") or parsed.get("names") or []
            return [str(item).strip()[:80] for item in items if str(item).strip()][:8]
        except json.JSONDecodeError:
            pass
    return [line.strip(" -•")[:80] for line in raw.splitlines() if line.strip()][:8]
