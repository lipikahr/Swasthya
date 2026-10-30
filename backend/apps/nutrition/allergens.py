"""Deterministic allergy and diet filters. The language model cannot override these."""

import re

ALLERGEN_ALIASES = {
    "milk": {"milk", "dairy", "lactose", "curd", "dahi", "ghee", "butter", "cheese", "paneer", "cream", "yogurt", "yoghurt", "khoa", "khoya", "whey"},
    "egg": {"egg", "eggs", "omelette", "omelet"},
    "peanut": {"peanut", "peanuts", "groundnut", "groundnuts", "mungfali"},
    "tree nut": {"almond", "cashew", "walnut", "pistachio", "hazelnut", "nut", "nuts"},
    "wheat": {"wheat", "gluten", "atta", "maida", "chapati", "roti", "naan", "bread", "biscuit", "semolina", "rava", "sooji", "suji", "upma"},
    "soy": {"soy", "soya", "tofu"},
    "fish": {"fish", "machli", "machhi", "salmon", "tuna", "pomfret"},
    "shellfish": {"prawn", "shrimp", "crab", "lobster", "shellfish"},
    "sesame": {"sesame", "til"},
    "mustard": {"mustard", "sarson"},
}

MEAT_TOKENS = {
    "chicken",
    "mutton",
    "lamb",
    "beef",
    "pork",
    "fish",
    "prawn",
    "shrimp",
    "egg",
    "eggs",
    "omelette",
    "keema",
    "mutton",
    "meat",
    "turkey",
    "bacon",
}
DAIRY_TOKENS = ALLERGEN_ALIASES["milk"]


def normalize_allergen(value: str) -> str:
    text = " ".join(str(value or "").strip().casefold().split())
    if not text:
        return ""
    for canonical, aliases in ALLERGEN_ALIASES.items():
        if text == canonical or text in aliases:
            return canonical
    return text


def tokens(name: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (name or "").casefold()))


def allergen_conflict(food_name: str, allergies: list[str]) -> str | None:
    name_tokens = tokens(food_name)
    for allergy in allergies:
        canonical = normalize_allergen(allergy)
        aliases = ALLERGEN_ALIASES.get(canonical, {canonical})
        if name_tokens & set(aliases) or canonical.replace(" ", "") in food_name.casefold().replace(" ", ""):
            return canonical
    return None


def diet_conflict(food_name: str, diet: str) -> str | None:
    name_tokens = tokens(food_name)
    if diet == "vegetarian" and name_tokens & (MEAT_TOKENS - {"egg", "eggs", "omelette"}):
        return "vegetarian"
    if diet == "vegan" and name_tokens & (MEAT_TOKENS | DAIRY_TOKENS):
        return "vegan"
    return None


def dislike_conflict(food_name: str, dislikes: list[str]) -> str | None:
    folded = food_name.casefold()
    for dislike in dislikes:
        text = str(dislike or "").strip().casefold()
        if len(text) >= 3 and text in folded:
            return text
    return None


ONION_TOKENS = {"onion", "onions", "pyaz", "pyaaz"}
GARLIC_TOKENS = {"garlic", "lehsun", "lahsun"}
JAIN_ROOT_TOKENS = ONION_TOKENS | GARLIC_TOKENS | {
    "potato",
    "potatoes",
    "aloo",
    "carrot",
    "beet",
    "beetroot",
    "radish",
    "ginger",
    "garlic",
    "onion",
}
RESTRICTION_ALIASES = {
    "vegetarian": "vegetarian",
    "vegan": "vegan",
    "jain": "jain",
    "no onion": "no onion",
    "no-onion": "no onion",
    "no garlic": "no garlic",
    "no-garlic": "no garlic",
}


def normalize_restriction(value: str) -> str:
    text = " ".join(str(value or "").strip().casefold().split())
    if text.startswith("custom:"):
        return text[:80]
    return RESTRICTION_ALIASES.get(text, text)


def restriction_conflict(text: str, restrictions: list[str]) -> str | None:
    name_tokens = tokens(text)
    folded = text.casefold()
    for raw in restrictions:
        restriction = normalize_restriction(raw)
        if not restriction:
            continue
        if restriction == "vegetarian" and name_tokens & (MEAT_TOKENS - {"egg", "eggs", "omelette"}):
            return "vegetarian"
        if restriction == "vegan" and name_tokens & (MEAT_TOKENS | DAIRY_TOKENS):
            return "vegan"
        if restriction == "jain" and name_tokens & JAIN_ROOT_TOKENS:
            return "jain"
        if restriction == "no onion" and name_tokens & ONION_TOKENS:
            return "no onion"
        if restriction == "no garlic" and name_tokens & GARLIC_TOKENS:
            return "no garlic"
        if restriction.startswith("custom:"):
            custom = restriction.split(":", 1)[1].strip()
            if len(custom) >= 3 and custom in folded:
                return custom
    return None


def exclusion_reason(*, name: str, ingredients: str, profile) -> str | None:
    haystack = f"{name} {ingredients or ''}".strip()
    allergies = list(getattr(profile, "allergies", None) or []) if profile else []
    dislikes = list(getattr(profile, "dislikes", None) or []) if profile else []
    restrictions = list(getattr(profile, "restrictions", None) or []) if profile else []
    diet = getattr(profile, "diet_pattern", "") if profile else ""
    hit = allergen_conflict(haystack, allergies)
    if hit:
        return f"allergy:{hit}"
    hit = restriction_conflict(haystack, restrictions)
    if hit:
        return f"restriction:{hit}"
    hit = diet_conflict(haystack, diet)
    if hit:
        return f"diet:{hit}"
    hit = dislike_conflict(haystack, dislikes)
    if hit:
        return f"dislike:{hit}"
    return None


def suggestion_allowed(*, name: str, ingredients: str, profile, require_ingredients: bool = False) -> tuple[bool, str]:
    if require_ingredients and not str(ingredients or "").strip():
        return False, "unverified"
    reason = exclusion_reason(name=name, ingredients=ingredients, profile=profile)
    if reason:
        return False, reason
    return True, "ok"
