import re

from django.db.models import Q

from .calculation import active_version
from .embeddings import similar_foods
from .models import Food
from .normalize import food_tokens, has_indic_letters, normalize_alias

# Household amounts and filler words are not food names. Semantic search must
# not turn "350g" or "one plate" into the nearest unrelated foods.
_NOT_FOOD_WORDS = {
    "a",
    "an",
    "the",
    "of",
    "about",
    "around",
    "approximately",
    "approx",
    "roughly",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "plate",
    "plates",
    "bowl",
    "bowls",
    "glass",
    "glasses",
    "cup",
    "cups",
    "spoon",
    "spoons",
    "piece",
    "pieces",
    "serving",
    "servings",
    "gram",
    "grams",
    "kilogram",
    "kilograms",
    "kg",
    "kgs",
    "g",
    "some",
    "bit",
    "little",
}


def _query_words_match_name(query: str, food_name: str) -> bool:
    """A short fragment such as "hi" must not match every name that contains those letters."""
    tokens = [token for token in food_tokens(query) if len(token) >= 3]
    if not tokens:
        return False
    name_tokens = set(food_tokens(food_name))
    return all(any(token == item or token in item or item in token for item in name_tokens) for token in tokens)


def meaningful_food_query(query: str) -> bool:
    if has_indic_letters(query or ""):
        tokens = food_tokens(query)
        quantity_like = {
            "ಒಂದು",
            "ಎರಡು",
            "ಮೂರು",
            "ಗ್ರಾಂ",
            "एक",
            "दो",
            "तीन",
            "ग्राम",
            "ஒன்று",
            "இரண்டு",
            "கிராம்",
            "రెండు",
            "గ్రాము",
        }
        return any(token not in quantity_like and not token.isdigit() for token in tokens)
    words = re.findall(r"[A-Za-z]+", query or "")
    return any(word.casefold() not in _NOT_FOOD_WORDS and len(word) > 1 for word in words)


def suggest_foods(query: str, limit: int = 5):
    """Prefix autocomplete for the composer. Does not run the meal agent."""
    text = query.strip()
    if len(text) < 2 or not meaningful_food_query(text):
        return []
    version = active_version()
    cap = min(max(int(limit), 1), 5)
    folded = normalize_alias(text)
    matches = list(
        Food.objects.filter(nutrition_rows__dataset_version=version)
        .filter(
            Q(food_name__icontains=text)
            | Q(food_code__istartswith=text)
            | Q(aliases__verified=True, aliases__normalized_alias__icontains=folded)
        )
        .distinct()
        .order_by("food_name", "food_code")[:40]
    )
    folded = text.casefold()
    prefix = []
    rest = []
    for food in matches:
        tokens = re.findall(r"[a-z0-9]+", food.food_name.casefold())
        if food.food_name.casefold().startswith(folded) or any(token.startswith(folded) for token in tokens):
            prefix.append(food)
        else:
            rest.append(food)
        if len(prefix) >= cap:
            break
    return (prefix + rest)[:cap]


def search_food(query: str, limit: int = 25, embed=None):
    version = active_version()
    text = query.strip()
    folded = normalize_alias(text)
    textual = list(
        Food.objects.filter(nutrition_rows__dataset_version=version)
        .filter(
            Q(food_name__icontains=text)
            | Q(food_code__iexact=text)
            | Q(aliases__verified=True, aliases__normalized_alias=folded)
        )
        .distinct()
        .order_by("food_name", "food_code")[:limit]
    )
    if len(textual) >= limit:
        return textual
    seen = {food.id for food in textual}
    for food in similar_foods(text, version, limit=limit, embed=embed):
        if food.id not in seen:
            textual.append(food)
            seen.add(food.id)
        if len(textual) >= limit:
            break
    return textual


def resolve_food(query: str, embed=None, semantic: bool = True) -> dict:
    """Pick one food only when the query matches a single verified record."""
    version = active_version()
    text = query.strip()
    foods = Food.objects.filter(nutrition_rows__dataset_version=version)
    exact_code = foods.filter(food_code__iexact=text).first()
    if exact_code is not None:
        return {"status": "resolved", "food": exact_code}

    exact_name = list(foods.filter(food_name__iexact=text).order_by("food_name")[:10])
    if len(exact_name) == 1:
        return {"status": "resolved", "food": exact_name[0]}
    if len(exact_name) > 1:
        return {"status": "ambiguous", "foods": exact_name[:3]}

    if len(text) < 3:
        return {"status": "not_found", "foods": []}

    partial = [
        food
        for food in foods.filter(food_name__icontains=text).order_by("food_name")[:40]
        if _query_words_match_name(text, food.food_name)
    ][:3]
    if len(partial) == 1:
        return {"status": "resolved", "food": partial[0]}
    if len(partial) > 1:
        return {"status": "ambiguous", "foods": partial}
    if not semantic or not meaningful_food_query(text):
        return {"status": "not_found", "foods": []}

    neighbors = similar_foods(text, version, embed=embed)
    related = [
        food
        for food in neighbors
        if _query_words_match_name(text, food.food_name)
    ]
    if len(related) == 1:
        return {"status": "resolved", "food": related[0]}
    if len(related) > 1:
        return {"status": "ambiguous", "foods": related[:5]}
    return {"status": "not_found", "foods": []}
