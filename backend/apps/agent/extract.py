"""Extract food names, quantities, and meal categories from user text.

The original sentence is not rewritten. Search uses the extracted food name.
"""

from __future__ import annotations

import re

from apps.nutrition.normalize import fold_digits, has_indic_letters, normalize_alias

MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}

_MEAL_ALIASES = (
    (re.compile(r"\bfor\s+(breakfast|lunch|dinner|snack)\b", re.I), None),
    (re.compile(r"\b(breakfast|lunch|dinner|snack)\b", re.I), None),
    (re.compile(r"ನಾಸ್ತೆ|ಉಪಾಹಾರ|ಬ್ರೇಕ್[\s\-]?ಫಾಸ್ಟ್", re.I), "breakfast"),
    (re.compile(r"नाश्त[ाेैं]*|नाश्ते", re.I), "breakfast"),
    (re.compile(r"காலை\s*உணவு", re.I), "breakfast"),
    (re.compile(r"అల్పాహారం|ఉదయం\s*భోజనం", re.I), "breakfast"),
    (re.compile(r"ಊಟ|ಲಂಚ್", re.I), "lunch"),
    (re.compile(r"दोपहर|लंच", re.I), "lunch"),
    (re.compile(r"மதிய\s*உணவு", re.I), "lunch"),
    (re.compile(r"భోజనం|లంచ్", re.I), "lunch"),
    (re.compile(r"ರಾತ್ರಿ\s*ಊಟ|ಡಿನರ್", re.I), "dinner"),
    (re.compile(r"रात का खाना|डिनर", re.I), "dinner"),
    (re.compile(r"இரவு\s*உணவு", re.I), "dinner"),
    (re.compile(r"రాత్రి\s*భోజనం", re.I), "dinner"),
    (re.compile(r"ತಿಂಡಿ|ಸ್ನ್ಯಾಕ್", re.I), "snack"),
    (re.compile(r"नाश्ता(?!\s*में)|स्नैक", re.I), "snack"),
)

_QUANTITY_WORDS = {
    "a": "1",
    "an": "1",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "ಒಂದು": "1",
    "ಎರಡು": "2",
    "ಮೂರು": "3",
    "ನಾಲ್ಕು": "4",
    "ಐದು": "5",
    "एक": "1",
    "दो": "2",
    "तीन": "3",
    "चार": "4",
    "पांच": "5",
    "ஒன்று": "1",
    "ஒரு": "1",
    "இரண்டு": "2",
    "மூன்று": "3",
    "ఒక": "1",
    "ఒకటి": "1",
    "రెండు": "2",
    "మూడు": "3",
    "এক": "1",
    "দুই": "2",
    "তিন": "3",
}

_UNIT_ALIASES = {
    "g": "g",
    "gram": "g",
    "grams": "g",
    "ಗ್ರಾಂ": "g",
    "ग्राम": "g",
    "கிராம்": "g",
    "గ్రాములు": "g",
    "గ్రాము": "g",
    "গ্রাম": "g",
    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "ಕೆಜಿ": "kg",
    "किलो": "kg",
    "किलोग्राम": "kg",
}

_FILLER = re.compile(
    r"^(?:ನಾನು|ನಾವು|ಮತ್ತು|ಮೇಲೆ|"
    r"मैंने|मैं|हमने|और|"
    r"நான்|நாங்கள்|"
    r"నేను|మేము|"
    r"আমি|আমরা)\s+",
)
_EATEN = re.compile(
    r"\s+(?:ತಿಂದೆ|ತಿಂದೆವು|ತಿಂದಿದ್ದೇನೆ|ತಿನ್ನುತ್ತಿದ್ದೇನೆ|ಸೇವಿಸಿದೆ|"
    r"खाईं|खाई|खाया|खाये|खाए|खा|"
    r"சாப்பிட்டேன்|சாப்பிட்டோம்|"
    r"తిన్నాను|తిన్నాం|"
    r"খেয়েছি|খেলাম)[.।]*$",
)


def extract_mentions(text: str) -> dict:
    original = " ".join(str(text or "").strip().split())
    cleaned = fold_digits(original)
    meal_type, cleaned = _strip_meal_type(cleaned)
    english = _english_mentions(cleaned, meal_type)
    indic = _indic_mentions(cleaned, meal_type)
    if has_indic_letters(cleaned) and indic["items"] and _looks_like_food_name(indic["items"][0]["food_query"]):
        return indic
    if english["items"] and _looks_like_food_name(english["items"][0]["food_query"]):
        return english
    if indic["items"]:
        return indic
    if english["items"]:
        return english
    return {"meal_type": meal_type, "items": [], "original_text": original}


def _looks_like_food_name(query: str) -> bool:
    text = query or ""
    if re.search(r"\b(?:i|we|ate|had|eaten|for|please)\b", text, re.I):
        return False
    if re.search(r"ನಾನು|ತಿಂದೆ|मैंने|खाई|खाया|நான்|சாப்பிட்ட|నేను|తిన్న", text):
        return False
    return True


def _english_mentions(text: str, meal_type: str | None) -> dict:
    from .providers import normalize_mention

    cleaned = " ".join(text.strip().split())
    if meal_type is None:
        meal_match = re.search(r"\bfor\s+(breakfast|lunch|dinner|snack)\b", cleaned, re.I)
        if meal_match:
            meal_type = meal_match.group(1).lower()
            cleaned = f"{cleaned[: meal_match.start()]} {cleaned[meal_match.end():]}"
            cleaned = " ".join(cleaned.split())
    stripped = re.sub(
        r"^(?:i\s+)?(?:just\s+)?(?:have\s+eaten|ate|had|eaten)\s+",
        "",
        cleaned,
        flags=re.I,
    ).strip(" .")
    if not stripped:
        return {"meal_type": meal_type, "items": []}
    items = []
    for part in re.split(r"\s+and\s+", stripped, flags=re.I):
        query, quantity, unit = normalize_mention(part.strip(" ."))
        if query:
            items.append(
                {
                    "food_query": query,
                    "quantity": quantity,
                    "unit": unit,
                    "original_query": query,
                }
            )
    return {"meal_type": meal_type, "items": items}


def _indic_mentions(text: str, meal_type: str | None) -> dict:
    cleaned = _FILLER.sub("", text.strip())
    cleaned = _EATEN.sub("", cleaned).strip(" .।")
    cleaned = re.sub(r"^(?:में|ನಲ್ಲಿ|లో|இல்)\s+", "", cleaned)
    quantity, unit, rest = _split_quantity(cleaned)
    food = rest.strip(" .।")
    if not food:
        return {"meal_type": meal_type, "items": []}
    return {
        "meal_type": meal_type,
        "items": [
            {
                "food_query": food,
                "quantity": quantity,
                "unit": unit,
                "original_query": food,
            }
        ],
    }


def _strip_meal_type(text: str) -> tuple[str | None, str]:
    cleaned = text
    found = None
    for pattern, mapped in _MEAL_ALIASES:
        match = pattern.search(cleaned)
        if not match:
            continue
        found = mapped or match.group(1).lower()
        if found not in MEAL_TYPES:
            continue
        cleaned = f"{cleaned[: match.start()]} {cleaned[match.end() :]}"
        cleaned = " ".join(cleaned.split())
        break
    return found, cleaned


def _split_quantity(text: str) -> tuple[str | None, str | None, str]:
    cleaned = " ".join(text.split())
    match = re.match(
        r"^(?P<qty>\d+(?:\.\d+)?|" + "|".join(map(re.escape, sorted(_QUANTITY_WORDS, key=len, reverse=True))) + r")"
        r"(?:\s+(?P<unit>" + "|".join(map(re.escape, sorted(_UNIT_ALIASES, key=len, reverse=True))) + r"))?"
        r"(?:\s+)?",
        cleaned,
        flags=re.I,
    )
    if not match:
        return None, None, cleaned
    raw_qty = match.group("qty")
    quantity = _QUANTITY_WORDS.get(raw_qty, _QUANTITY_WORDS.get(raw_qty.casefold(), raw_qty))
    raw_unit = match.group("unit")
    unit = _UNIT_ALIASES.get(raw_unit, _UNIT_ALIASES.get((raw_unit or "").casefold(), None)) if raw_unit else None
    rest = cleaned[match.end() :].strip(" .।")
    rest = re.sub(r"^(?:में|ನಲ್ಲಿ|లో|இல்)\s+", "", rest)
    return quantity, unit, rest
