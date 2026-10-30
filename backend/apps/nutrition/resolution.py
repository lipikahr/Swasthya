"""Identify a verified catalogue food from an extracted name.

Translation and aliases only help locate candidates. Nutrition still comes
from the matched Anuvaad row.
"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher

from django.db.models import Q

from .calculation import active_version
from .embeddings import similar_foods
from .models import Food, FoodAlias
from .normalize import food_tokens, has_indic_letters, normalize_alias
from .search import meaningful_food_query

logger = logging.getLogger(__name__)

_FILLER = {"the", "a", "an", "of", "please", "food", "one", "kind", "some"}


def resolve_food_mention(query: str, *, language: str | None = None, embed=None, semantic: bool = True) -> dict:
    text = str(query or "").strip()
    if not text:
        return {"status": "not_found", "foods": []}
    version = active_version()
    foods = Food.objects.filter(nutrition_rows__dataset_version=version)
    exact_code = foods.filter(food_code__iexact=text).first()
    if exact_code is not None:
        return {"status": "resolved", "food": exact_code}

    for candidate in _search_forms(text, language):
        matched = _lexical_match(foods, candidate)
        if matched["status"] != "not_found":
            return matched

    translated = _search_translation(text, language)
    if translated and normalize_alias(translated) != normalize_alias(text):
        logger.info("food_search_translated language=%s", language or "")
        for candidate in _search_forms(translated, "en"):
            matched = _lexical_match(foods, candidate)
            if matched["status"] != "not_found":
                return matched

    if len(text) < 2 or not meaningful_food_query(text):
        return {"status": "not_found", "foods": []}

    if semantic:
        neighbors = similar_foods(text, version, embed=embed)
        related = _related_foods(text, neighbors)
        if len(related) == 1:
            return {"status": "resolved", "food": related[0]}
        if len(related) > 1:
            return {"status": "ambiguous", "foods": related[:5]}
    return {"status": "not_found", "foods": []}


def _lexical_match(foods, text: str) -> dict:
    folded = normalize_alias(text)
    if not folded:
        return {"status": "not_found", "foods": []}

    exact_name = [food for food in foods.filter(food_name__iexact=text).order_by("food_name", "food_code")[:10]]
    if not exact_name:
        exact_name = [
            food
            for food in foods.order_by("food_name", "food_code")[:800]
            if normalize_alias(food.food_name) == folded
        ][:10]
    if len(exact_name) == 1:
        return {"status": "resolved", "food": exact_name[0]}
    if len(exact_name) > 1:
        return {"status": "ambiguous", "foods": exact_name[:3]}

    aliases = list(
        FoodAlias.objects.filter(verified=True).filter(Q(normalized_alias=folded) | Q(alias_text__iexact=text))
        .select_related("food")
        .order_by("food__food_name", "food__food_code")[:10]
    )
    alias_foods = []
    seen = set()
    for alias in aliases:
        if alias.food_id in seen:
            continue
        if not foods.filter(pk=alias.food_id).exists():
            continue
        seen.add(alias.food_id)
        alias_foods.append(alias.food)
    if len(alias_foods) == 1:
        return {"status": "resolved", "food": alias_foods[0]}
    if len(alias_foods) > 1:
        return {"status": "ambiguous", "foods": alias_foods[:3]}

    if len(folded) < 3 and not has_indic_letters(text):
        return {"status": "not_found", "foods": []}

    tokens = [token for token in food_tokens(text) if token.casefold() not in _FILLER]
    if not tokens:
        return {"status": "not_found", "foods": []}

    query = Q()
    for token in tokens[:4]:
        query |= Q(food_name__icontains=token)
        query |= Q(aliases__verified=True, aliases__normalized_alias__icontains=token)
    partial = []
    seen = set()
    for food in foods.filter(query).distinct().order_by("food_name", "food_code")[:40]:
        if food.id in seen:
            continue
        if _tokens_match(tokens, food):
            seen.add(food.id)
            partial.append(food)
        if len(partial) >= 3:
            break
    if len(partial) == 1:
        return {"status": "resolved", "food": partial[0]}
    if len(partial) > 1:
        return {"status": "ambiguous", "foods": partial}

    fuzzy = _fuzzy_candidates(foods, folded)
    if len(fuzzy) == 1:
        return {"status": "resolved", "food": fuzzy[0]}
    if len(fuzzy) > 1:
        return {"status": "ambiguous", "foods": fuzzy[:3]}
    return {"status": "not_found", "foods": []}


def _tokens_match(tokens: list[str], food: Food) -> bool:
    name_tokens = set(food_tokens(food.food_name))
    alias_tokens = set()
    for alias in food.aliases.filter(verified=True).values_list("normalized_alias", flat=True)[:20]:
        alias_tokens.update(food_tokens(alias))
    haystack = name_tokens | alias_tokens
    return all(any(token == item or token in item or item in token for item in haystack) for token in tokens)


def _fuzzy_candidates(foods, folded: str) -> list[Food]:
    if len(folded) < 4:
        return []
    scored = []
    names = foods.only("id", "food_name", "food_code").order_by("food_name")[:400]
    for food in names:
        ratio = SequenceMatcher(None, folded, normalize_alias(food.food_name)).ratio()
        if ratio >= 0.88:
            scored.append((ratio, food))
    scored.sort(key=lambda item: (-item[0], item[1].food_name))
    return [food for _ratio, food in scored[:3]]


def _related_foods(query: str, foods: list) -> list:
    tokens = [token for token in food_tokens(query) if len(token) > 2 and token.casefold() not in _FILLER]
    if not tokens:
        return []
    related = []
    for food in foods:
        name_tokens = set(food_tokens(food.food_name))
        if any(any(token == item or token in item or item in token for item in name_tokens) for token in tokens):
            related.append(food)
    return related


def _search_forms(query: str, language: str | None) -> list[str]:
    forms = [query]
    singular = _singular(query)
    if singular != query:
        forms.append(singular)
    return forms


def _singular(text: str) -> str:
    stripped = text.strip()
    folded = stripped.casefold()
    if folded.endswith("s") and not folded.endswith("ss") and len(stripped) > 3 and stripped.isascii():
        return stripped[:-1]
    return stripped


def _search_translation(text: str, language: str | None) -> str | None:
    if not language or language == "en" or not has_indic_letters(text):
        return None
    try:
        from apps.agent.languages import translate_for_search

        return translate_for_search(text, language)
    except Exception:
        logger.info("food_search_translation_skipped language=%s", language or "")
        return None
