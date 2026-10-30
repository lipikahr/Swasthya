"""LangGraph workflow for one text meal message.

A pending meal is stored on the conversation. A later reply that chooses a food
or gives a quantity updates that draft. It is not extracted as a new meal.
A resolved draft waits for confirmation and is not a consumed meal. The draft
is removed only after the meal has been saved. Nodes do not read a user id
from the model output.
"""

import copy
import re
from datetime import timedelta
from typing import TypedDict

from django.db import transaction
from django.utils import timezone
from langgraph.graph import END, START, StateGraph
from rest_framework.exceptions import NotFound, ValidationError

from apps.conversations.models import AgentAction, Conversation, MealDraft, Message
from apps.meals.services import create_food_log
from apps.nutrition.calculation import WEIGHT_TO_GRAMS, NutritionError, calculate_nutrition, calculate_user_food
from apps.nutrition.models import Food, UserFood
from apps.nutrition.nutrients import NUTRIENT_FIELDS
from apps.nutrition.normalize import food_tokens, has_indic_letters
from apps.nutrition.resolution import resolve_food_mention
from apps.nutrition.search import meaningful_food_query
from apps.progress.goal import day_goal_status, record_new_achievement
from apps.progress.services import get_daily_progress
from apps.profiles.models import UserProfile

from .extract import extract_mentions
from .languages import detect_language, localize_reply, working_text_for_model
from .providers import ProviderError, clean_food_query, get_provider, parse_quantity_reply
from .suggestions import is_suggestion_request, suggest_foods_for_user

_LEADING_PORTION = re.compile(
    r"^(?:(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?)\s+)?"
    r"(?:plates|plate|bowls|bowl|glasses|glass|cups|cup|spoons|spoon|pieces|piece|servings|serving)\s+(?:of\s+)?",
    re.IGNORECASE,
)
_CANCEL = re.compile(
    r"^(?:please\s+)?(?:cancel|stop|nevermind|never mind|forget it|do not log(?: that)?|don't log(?: that)?)[.!?]*$",
    re.IGNORECASE,
)
_RETRY = re.compile(r"^(?:try again|retry|yes|log it|save it)[.!?]*$", re.IGNORECASE)
_CORRECTION = re.compile(r"^(?:actually|instead|i meant|no,?|not that,?)\s+", re.IGNORECASE)
_TOKEN_ALIASES = {"rava": "semolina", "semolina": "rava", "sooji": "semolina", "suji": "semolina"}
_CHOICE_FILLER = {"the", "a", "an", "of", "please", "food", "one", "kind"}
CONFIRM_MEAL_TYPES = frozenset({"breakfast", "lunch", "dinner", "snack"})
DRAFT_TTL = timedelta(hours=24)
_MEAL_ONLY = re.compile(r"^(?:for\s+|as\s+)?(breakfast|lunch|dinner|snack)[.!?]*$", re.IGNORECASE)
_INFO_PROGRESS = re.compile(
    r"\b(what did i eat|remaining|how am i doing|today's progress|todays progress|weekly progress|yesterday)\b",
    re.IGNORECASE,
)
_INFO_PLAN = re.compile(r"\b(generate (?:a )?plan|meal plan|plan (?:for )?today|suggest a plan)\b", re.IGNORECASE)


class AgentState(TypedDict, total=False):
    user_id: int
    conversation_id: int
    text: str
    provider: str
    meal_type: str | None
    mentions: list
    draft_items: list
    resolved: list
    status: str
    reply: str
    meal_id: int | None
    reason: str
    confirmation: dict | None
    suggestions: list
    language: str
    allergy_note: str


def run_text_turn(*, user_id: int, conversation_id: int, text: str) -> AgentState:
    result = _graph.invoke(
        {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "text": text,
            "meal_id": None,
        }
    )
    return result


_SOCIAL_WORDS = {
    "a",
    "an",
    "the",
    "hi",
    "hii",
    "hello",
    "hey",
    "good",
    "morning",
    "afternoon",
    "evening",
    "thanks",
    "thank",
    "you",
    "please",
    "ok",
    "okay",
    "bye",
    "goodbye",
    "there",
    "how",
    "are",
    "what",
    "whats",
    "up",
    "lot",
}
_MAX_FOOD_CHOICES = 3


def _social_reply(text: str) -> str | None:
    cleaned = text.strip(" .!?")
    if re.fullmatch(r"hi+|hello|hey+", cleaned, re.IGNORECASE):
        return "Hello. What did you eat?"
    match = re.fullmatch(r"good\s+(morning|afternoon|evening)", cleaned, re.IGNORECASE)
    if match:
        return f"Good {match.group(1).lower()}. What did you eat?"
    if re.fullmatch(r"thanks|thank\s+you", cleaned, re.IGNORECASE):
        return "You're welcome."
    words = re.findall(r"[a-z']+", cleaned.casefold())
    if words and all(word in _SOCIAL_WORDS for word in words):
        return "Describe a food and how much of it you ate, and I can log it."
    return None


def _preferred_language(user_id: int) -> str:
    profile = UserProfile.objects.filter(user_id=user_id).first()
    return getattr(profile, "preferred_language", "") or "en"


def extract_node(state: AgentState) -> dict:
    text = " ".join(state["text"].strip().split())
    language = detect_language(text, _preferred_language(state["user_id"]))
    draft = _get_draft(state)
    social = _social_reply(text)
    if social:
        return {
            "status": "NEEDS_CLARIFICATION",
            "reply": social,
            "provider": "conversation",
            "meal_type": draft.meal_type if draft is not None else None,
            "mentions": draft.items if draft is not None else [],
            "draft_items": draft.items if draft is not None else [],
            "meal_id": None,
            "language": language,
        }
    if _CANCEL.match(text):
        _delete_draft(state)
        return {
            "status": "NEEDS_CLARIFICATION",
            "reply": "Okay, I won't log that meal.",
            "provider": "draft",
            "meal_type": None,
            "mentions": [],
            "draft_items": [],
            "meal_id": None,
            "language": language,
        }
    if draft is not None and _expired(draft):
        _delete_draft(state)
        draft = None
    if draft is not None and draft.status in {"awaiting_confirmation", "ready"} and _all_ready(draft.items):
        pending = _pending_confirmation_turn(state, draft, text)
        pending["language"] = language
        return pending
    if draft is not None and _has_pending(draft.items):
        applied = _apply_pending_reply(draft, text)
        if applied is None:
            return {
                "status": "NEEDS_CLARIFICATION",
                "reply": _blocking_reply(draft.items),
                "provider": "draft",
                "meal_type": draft.meal_type or None,
                "mentions": draft.items,
                "draft_items": draft.items,
                "language": language,
            }
        return {**_draft_state(draft.meal_type, applied), "language": language}

    info = _information_turn(state, text, language)
    if info is not None:
        return info
    if is_suggestion_request(text):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.get(pk=state["user_id"])
        suggested = suggest_foods_for_user(user, _stated_meal_type(text))
        suggested["language"] = language
        suggested["provider"] = "suggestions"
        return suggested
    local = extract_mentions(text)
    provider = get_provider()
    working, internal = working_text_for_model(text, language)
    if internal:
        _record(state, "translate", "internal_en", {"original_chars": len(text)}, {"used": True, "language": language}, "ok")
    try:
        if local.get("items"):
            extracted = {
                "provider": provider.name,
                "items": local["items"],
                "meal_type": local.get("meal_type"),
            }
        else:
            extracted = provider.extract(working)
    except ProviderError as exc:
        output = {"error": str(exc), "reason": getattr(exc, "reason", "provider")}
        output.update(
            {
                key: value
                for key, value in getattr(exc, "details", {}).items()
                if key in {"exception", "http_code", "status", "reason", "upstream"} and value not in (None, "")
            }
        )
        _record(state, "extract", provider.name, {"char_count": len(text)}, output, "error")
        return {
            "status": "ERROR",
            "reply": str(exc),
            "mentions": [],
            "draft_items": [],
            "provider": provider.name,
            "reason": getattr(exc, "reason", "provider"),
            "language": language,
        }
    items = [_item_from_mention(mention) for mention in extracted["items"]]
    items = [item for item in items if item["food_query"] or item["quantity"]]
    for item in items:
        item["language"] = language
        item.setdefault("original_query", item.get("food_query"))
        item.setdefault("search_query", item.get("food_query"))
    meal_type = _stated_meal_type(text) or extracted.get("meal_type") or local.get("meal_type")
    _record(state, "extract", provider.name, {"char_count": len(text)}, {"item_count": len(items), "provider": provider.name}, "ok")
    if not items:
        return {
            "status": "NEEDS_CLARIFICATION",
            "reply": "Tell me the food and how much of it you ate.",
            "provider": extracted["provider"],
            "meal_type": meal_type,
            "mentions": [],
            "draft_items": [],
            "language": language,
        }
    return {
        "provider": extracted["provider"],
        "meal_type": meal_type,
        "mentions": items,
        "draft_items": items,
        "status": "",
        "reply": "",
        "language": language,
    }


def resolve_node(state: AgentState) -> dict:
    resolved = []
    for item in state.get("draft_items") or []:
        if item.get("status") == "ready" and item.get("food_code") and item.get("quantity") and item.get("unit"):
            resolved.append(item)
        else:
            resolved.append(_resolve_draft_item(state, item))
    blocking = next((item for item in resolved if item["status"] != "ready"), None)
    if blocking is None:
        meal_type = _confirmable(state.get("meal_type")) or ""
        try:
            confirmation = build_confirmation(meal_type, resolved)
        except NutritionError as exc:
            for item in resolved:
                item["status"] = "awaiting_quantity"
                item["reply"] = str(exc)
            _save_draft(state, meal_type, resolved, "awaiting_quantity")
            return {
                "resolved": resolved,
                "draft_items": resolved,
                "status": "NEEDS_CLARIFICATION",
                "reply": str(exc),
                "meal_id": None,
            }
        _save_draft(state, meal_type, resolved, "awaiting_confirmation")
        return {
            "resolved": resolved,
            "draft_items": resolved,
            "status": "AWAITING_CONFIRMATION",
            "reply": "Check this meal before I log it.",
            "confirmation": confirmation,
            "meal_id": None,
        }
    if _should_store(resolved):
        _save_draft(state, state.get("meal_type"), resolved, blocking["status"])
    return {
        "resolved": resolved,
        "draft_items": resolved,
        "status": "NEEDS_CLARIFICATION",
        "reply": blocking.get("reply") or "I need a bit more detail.",
    }


def respond_node(state: AgentState) -> dict:
    preferred = _preferred_language(state["user_id"]) if state.get("user_id") else ""
    language = preferred or state.get("language") or "en"
    reply = state.get("reply") or "I need a bit more detail."
    result = {
        "status": state.get("status") or "NEEDS_CLARIFICATION",
        "reply": localize_reply(reply, language),
        "language": language,
    }
    if state.get("confirmation") is not None:
        result["confirmation"] = state["confirmation"]
    if state.get("suggestions") is not None:
        result["suggestions"] = state["suggestions"]
    if state.get("allergy_note"):
        result["allergy_note"] = state["allergy_note"]
    return result


def _draft_state(meal_type: str | None, items: list) -> dict:
    return {
        "provider": "draft",
        "meal_type": meal_type or None,
        "mentions": items,
        "draft_items": items,
        "status": "",
        "reply": "",
    }


def _apply_pending_reply(draft: MealDraft, text: str) -> list | None:
    items = copy.deepcopy(draft.items)
    index = next(i for i, item in enumerate(items) if item.get("status") != "ready")
    item = items[index]
    status = item.get("status")
    parsed = parse_quantity_reply(text)
    quantity_only = parsed is not None and not meaningful_food_query(text)
    if status == "awaiting_choice":
        match = _match_candidate(text, item.get("candidates") or [])
        if match is not None:
            item["food_code"] = match["food_code"]
            item["food_name"] = match["food_name"]
            item["candidates"] = []
            item["status"] = "awaiting_quantity"
            items[index] = item
            return items
        if quantity_only:
            return None
        corrected = _correction_query(text)
        if meaningful_food_query(corrected):
            items[index] = _fresh_item(
                corrected,
                quantity=item.get("quantity"),
                unit=item.get("unit"),
                confirmed=bool(item.get("quantity_confirmed")),
            )
            return items
        return None
    if status == "awaiting_quantity" and item.get("food_code"):
        local = extract_mentions(text)
        local_item = (local.get("items") or [{}])[0] if local.get("items") else {}
        local_qty = local_item.get("quantity")
        if parsed is None and local_qty:
            parsed = {"quantity": local_qty, "unit": local_item.get("unit")}
        if parsed is not None and (quantity_only or _reply_matches_food(text, item) or local_qty):
            item["quantity"] = parsed["quantity"]
            if parsed.get("unit"):
                item["unit"] = parsed["unit"]
            item["quantity_confirmed"] = True
            item["status"] = "awaiting_quantity"
            items[index] = item
            return items
    corrected = _correction_query(text)
    if meaningful_food_query(corrected):
        kept_quantity = item.get("quantity") if item.get("quantity_confirmed") else None
        kept_unit = item.get("unit") if item.get("quantity_confirmed") else None
        items[index] = _fresh_item(corrected, quantity=kept_quantity, unit=kept_unit, confirmed=bool(kept_quantity))
        return items
    return None


def _resolve_draft_item(state: AgentState, item: dict) -> dict:
    if item.get("user_food_id"):
        return _finalize_user_food(state, item)
    if item.get("food_code"):
        return _finalize_known_food(state, item)
    query = str(item.get("food_query") or "").strip()
    if not meaningful_food_query(query):
        return {**item, "status": "not_found", "reply": "Tell me which food you ate."}
    resolution = _resolve_query(query, user_id=state.get("user_id"), language=item.get("language") or state.get("language"))
    _record(state, "resolve", "resolve_food", {"query": query}, {"status": resolution["status"]}, "ok")
    if resolution["status"] == "ambiguous":
        candidates = [
            {"food_code": food.food_code, "food_name": food.food_name}
            for food in resolution["foods"][:_MAX_FOOD_CHOICES]
        ]
        names = ", ".join(candidate["food_name"] for candidate in candidates)
        return {
            **item,
            "status": "awaiting_choice",
            "candidates": candidates,
            "reply": f"Which food did you mean? {names}.",
        }
    if resolution["status"] != "resolved":
        return {**item, "status": "not_found", "reply": f"I couldn't find {query} in the verified foods."}
    if resolution.get("user_food") is not None:
        user_food = resolution["user_food"]
        selected = {
            **item,
            "food_code": "",
            "user_food_id": user_food.id,
            "food_name": user_food.name,
            "candidates": [],
            "provenance": "user_provided",
        }
        return _finalize_user_food(state, selected)
    food = resolution["food"]
    selected = {**item, "food_code": food.food_code, "food_name": food.food_name, "candidates": [], "provenance": "verified"}
    return _finalize_known_food(state, selected)


def _finalize_user_food(state: AgentState, item: dict) -> dict:
    try:
        user_food = UserFood.objects.get(pk=item["user_food_id"], user_id=state["user_id"])
    except UserFood.DoesNotExist:
        return {**item, "status": "not_found", "reply": "I couldn't find that personal food."}
    quantity = item.get("quantity")
    if quantity in (None, ""):
        return {
            **item,
            "food_name": user_food.name,
            "status": "awaiting_quantity",
            "reply": f"How much {user_food.name} did you eat?",
        }
    unit = item.get("unit") or user_food.serving_unit
    try:
        calculated = calculate_user_food(user_food, quantity, unit)
    except NutritionError as exc:
        return {**item, "food_name": user_food.name, "status": "awaiting_quantity", "reply": str(exc)}
    return {
        **item,
        "status": "ready",
        "user_food_id": user_food.id,
        "food_code": "",
        "food_name": user_food.name,
        "quantity": str(calculated["quantity"]),
        "unit": calculated["unit"],
        "quantity_confirmed": True,
        "candidates": [],
        "provenance": "user_provided",
        "reply": "",
    }


def _finalize_known_food(state: AgentState, item: dict) -> dict:
    try:
        food = Food.objects.get(food_code=item["food_code"])
    except Food.DoesNotExist:
        return {**item, "status": "not_found", "reply": "I couldn't find that food in the verified foods."}
    quantity = item.get("quantity")
    if quantity in (None, ""):
        return {
            **item,
            "food_name": food.food_name,
            "status": "awaiting_quantity",
            "reply": f"How much {food.food_name} did you eat?",
        }
    unit = item.get("unit") or _inferred_unit(str(item.get("food_query") or ""), food.serving_unit)
    if not unit and item.get("quantity") and food.serving_unit:
        unit = food.serving_unit
    if not unit:
        verified = food.serving_unit or "a verified serving"
        return {
            **item,
            "food_name": food.food_name,
            "status": "awaiting_quantity",
            "reply": f"How much {food.food_name} did you eat? Grams, kilograms, or {verified} are the choices I can use.",
        }
    aligned = _aligned_unit(food, unit)
    if not item.get("quantity_confirmed") and not _unit_supported(food, aligned):
        return {
            **item,
            "food_name": food.food_name,
            "quantity": None,
            "unit": None,
            "status": "awaiting_quantity",
            "reply": f"How much {food.food_name} did you eat?",
        }
    try:
        calculated = calculate_nutrition(food.food_code, quantity, aligned)
    except NutritionError as exc:
        _record(
            state,
            "validate",
            "calculate_nutrition",
            {"food_code": food.food_code, "unit": aligned},
            {"code": exc.code},
            "error",
        )
        return {
            **item,
            "food_name": food.food_name,
            "status": "awaiting_quantity",
            "reply": str(exc),
        }
    return {
        **item,
        "status": "ready",
        "food_code": food.food_code,
        "food_name": food.food_name,
        "quantity": str(calculated["quantity"]),
        "unit": calculated["unit"],
        "quantity_confirmed": True,
        "candidates": [],
        "reply": "",
        "original_query": item.get("original_query") or item.get("food_query"),
        "search_query": item.get("search_query") or item.get("food_query"),
    }


def _item_from_mention(mention: dict) -> dict:
    raw_query = str(mention.get("food_query") or "").strip()
    quantity = mention.get("quantity")
    unit = None if mention.get("unit") in (None, "") else str(mention.get("unit")).lower()
    confirmed = False
    combined = raw_query
    if quantity not in (None, ""):
        combined = f"{quantity} {unit + ' ' if unit else ''}{raw_query}"
    original_query = str(mention.get("original_query") or raw_query).strip()
    parsed = parse_quantity_reply(combined)
    if parsed and parsed.get("unit") in {"g", "kg"}:
        quantity = parsed["quantity"]
        unit = parsed["unit"]
        confirmed = True
    elif quantity not in (None, "") and unit in WEIGHT_TO_GRAMS:
        quantity = str(quantity)
        unit = "g" if WEIGHT_TO_GRAMS[unit] == 1 else "kg"
        confirmed = True
    elif parsed and quantity not in (None, "") and unit is None:
        quantity = parsed["quantity"]
        unit = parsed["unit"]
        confirmed = False
    elif quantity not in (None, ""):
        quantity = str(quantity)
        confirmed = unit is None
    else:
        quantity = None
        unit = None
    item = _fresh_item(raw_query, quantity=quantity, unit=unit, confirmed=confirmed)
    item["original_query"] = original_query
    return item


def _fresh_item(query: str, quantity=None, unit=None, confirmed: bool = False) -> dict:
    parsed = parse_quantity_reply(query)
    if parsed and parsed.get("unit") in {"g", "kg"}:
        quantity = parsed["quantity"]
        unit = parsed["unit"]
        confirmed = True
    return {
        "food_query": _normalize_food_query(query),
        "original_query": str(query or "").strip(),
        "search_query": _normalize_food_query(query),
        "food_code": None,
        "food_name": None,
        "quantity": None if quantity in (None, "") else str(quantity),
        "unit": None if unit in (None, "") else str(unit).lower(),
        "quantity_confirmed": bool(confirmed and quantity not in (None, "")),
        "candidates": [],
        "status": "unresolved",
        "reply": "",
    }


def _normalize_food_query(query: str) -> str:
    text = _CORRECTION.sub("", " ".join(str(query or "").strip().split()))
    return clean_food_query(text)


def _correction_query(text: str) -> str:
    return _normalize_food_query(_CORRECTION.sub("", text.strip()))


def _match_candidate(text: str, candidates: list[dict]) -> dict | None:
    folded = _correction_query(text).casefold()
    if not folded or not candidates:
        return None
    exact = [candidate for candidate in candidates if candidate["food_name"].casefold() == folded]
    if len(exact) == 1:
        return exact[0]
    contained = []
    for candidate in candidates:
        name = candidate["food_name"].casefold()
        if folded in name or name in folded:
            contained.append(candidate)
    if len(contained) == 1:
        return contained[0]
    reply_tokens = [token for token in food_tokens(folded) if token not in _CHOICE_FILLER and len(token) > 2]
    scored = []
    for candidate in candidates:
        name_tokens = set(food_tokens(candidate["food_name"]))
        if reply_tokens and all(_token_matches(token, name_tokens) for token in reply_tokens):
            scored.append(candidate)
    if len(scored) == 1:
        return scored[0]
    return None


def _token_matches(token: str, name_tokens: set[str]) -> bool:
    options = {token, _TOKEN_ALIASES.get(token, token)}
    return bool(options & name_tokens)


def _reply_matches_food(text: str, item: dict) -> bool:
    name = str(item.get("food_name") or "").casefold()
    query = str(item.get("food_query") or "").casefold()
    folded = text.casefold()
    return bool(name and name in folded) or bool(query and query in folded)


def _resolve_query(query: str, user_id: int | None = None, language: str | None = None) -> dict:
    if not meaningful_food_query(query):
        return {"status": "not_found", "foods": []}
    if user_id:
        personal = UserFood.objects.filter(user_id=user_id, name__iexact=query).first()
        if personal is not None:
            return {"status": "resolved", "user_food": personal}
    last = {"status": "not_found", "foods": []}
    for candidate in _query_candidates(query):
        last = resolve_food_mention(candidate, language=language, semantic=False)
        if last["status"] != "not_found":
            return last
    if not meaningful_food_query(query):
        return {"status": "not_found", "foods": []}
    semantic = resolve_food_mention(_singular(query), language=language, semantic=True)
    if semantic["status"] != "ambiguous":
        return semantic
    related = _related_foods(query, semantic["foods"])
    if not related:
        return {"status": "not_found", "foods": []}
    return {"status": "ambiguous", "foods": related}


def _related_foods(query: str, foods: list) -> list:
    """Keep semantic neighbors that share a food word with the cleaned query."""
    tokens = [
        token
        for token in food_tokens(query)
        if len(token) > 2 and token not in _CHOICE_FILLER and token not in {"ate", "had", "eaten", "food"}
    ]
    if not tokens:
        return []
    related = []
    for food in foods:
        name_tokens = set(food_tokens(food.food_name))
        if any(_token_matches(token, name_tokens) for token in tokens):
            related.append(food)
    return related


def _query_candidates(query: str) -> list[str]:
    folded = _singular(query)
    if folded.casefold() == query.casefold():
        return [query]
    return [query, folded]


def _singular(text: str) -> str:
    stripped = text.strip()
    if stripped.casefold().endswith("s") and not stripped.casefold().endswith("ss") and len(stripped) > 3:
        return stripped[:-1]
    return stripped


def _inferred_unit(query: str, serving_unit: str) -> str | None:
    if serving_unit and _singular(query).casefold() == serving_unit.casefold():
        return serving_unit
    return None


def _unit_supported(food: Food, unit: str) -> bool:
    normalized = (unit or "").strip().lower()
    if normalized in WEIGHT_TO_GRAMS:
        return True
    serving = (food.serving_unit or "").strip().lower()
    if not serving:
        return False
    return normalized == serving or _singular(normalized) == serving or _singular(serving) == normalized


def _aligned_unit(food: Food, unit: str) -> str:
    normalized = (unit or "").strip().lower()
    if normalized in {"g", "gram", "grams"}:
        return "g"
    if normalized in {"kg", "kgs", "kilogram", "kilograms"}:
        return "kg"
    serving = (food.serving_unit or "").strip()
    if normalized in {"piece", "pieces"} and serving and serving.lower() not in WEIGHT_TO_GRAMS:
        return serving
    if serving and _unit_supported(food, normalized) and normalized not in WEIGHT_TO_GRAMS:
        return serving
    return normalized


def _has_pending(items: list) -> bool:
    return any(item.get("status") != "ready" for item in items)


def _all_ready(items: list) -> bool:
    return bool(items) and not _has_pending(items)


def _should_store(items: list) -> bool:
    return any(
        item.get("food_code") or item.get("candidates") or meaningful_food_query(item.get("food_query") or "")
        for item in items
    )


def _blocking_reply(items: list) -> str:
    for item in items:
        if item.get("status") != "ready" and item.get("reply"):
            return item["reply"]
    return "I need a bit more detail."


def _get_draft(state: AgentState) -> MealDraft | None:
    return MealDraft.objects.filter(conversation_id=state["conversation_id"], user_id=state["user_id"]).first()


def _lock_conversation(state: AgentState) -> Conversation:
    return Conversation.objects.select_for_update().get(pk=state["conversation_id"], user_id=state["user_id"])


def _save_draft(state: AgentState, meal_type: str | None, items: list, status: str) -> None:
    with transaction.atomic():
        conversation = _lock_conversation(state)
        MealDraft.objects.update_or_create(
            conversation=conversation,
            defaults={
                "user_id": state["user_id"],
                "meal_type": meal_type or "",
                "status": status,
                "language": state.get("language") or "",
                "original_text": state.get("text") or "",
                "items": items,
            },
        )


def _delete_draft(state: AgentState) -> None:
    with transaction.atomic():
        _lock_conversation(state)
        MealDraft.objects.filter(conversation_id=state["conversation_id"], user_id=state["user_id"]).delete()


def _record(state, action_type, tool_name, tool_input, tool_output, status) -> None:
    conversation = Conversation.objects.get(pk=state["conversation_id"])
    AgentAction.objects.create(
        conversation=conversation,
        action_type=action_type,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        status=status,
    )


def _after_extract(state: AgentState) -> str:
    if state.get("status") in {"ERROR", "NEEDS_CLARIFICATION", "AWAITING_CONFIRMATION", "SUGGESTIONS"}:
        return "respond"
    return "resolve"


def _build():
    graph = StateGraph(AgentState)
    graph.add_node("extract", extract_node)
    graph.add_node("resolve", resolve_node)
    graph.add_node("respond", respond_node)
    graph.add_edge(START, "extract")
    graph.add_conditional_edges("extract", _after_extract, {"resolve": "resolve", "respond": "respond"})
    graph.add_edge("resolve", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


_graph = _build()


def _stated_meal_type(text: str) -> str | None:
    """Use a category only when the user named breakfast, lunch, dinner, or snack."""
    match = re.search(r"\b(breakfast|lunch|dinner|snack)\b", text or "", re.IGNORECASE)
    return match.group(1).lower() if match else None


def _information_turn(state: AgentState, text: str, language: str) -> dict | None:
    from django.contrib.auth import get_user_model

    from apps.meals.plan_services import generate_day_plan

    user = get_user_model().objects.get(pk=state["user_id"])
    if _INFO_PLAN.search(text):
        try:
            plan = generate_day_plan(user)
        except ValidationError as exc:
            reply = " ".join(str(item) for item in exc.detail) if hasattr(exc, "detail") else str(exc)
            return {
                "status": "NEEDS_CLARIFICATION",
                "reply": reply,
                "provider": "plan",
                "meal_id": None,
                "language": language,
            }
        names = ", ".join(f"{slot['slot']}: {slot['food_name']}" for slot in plan.get("slots") or [])
        reply = plan.get("limitation") or f"Here is today's food plan. {names}. Log this from Plan after you confirm the meal."
        return {
            "status": "NEEDS_CLARIFICATION",
            "reply": reply,
            "provider": "plan",
            "meal_id": None,
            "language": language,
        }
    if not _INFO_PROGRESS.search(text):
        return None
    on_date = timezone.now().date()
    if "yesterday" in text.casefold():
        on_date = on_date - timedelta(days=1)
    progress = day_goal_status(user, on_date)
    consumed = progress["consumed"].get("energy_kcal")
    remaining = (progress.get("remaining") or {}).get("calories")
    reply = (
        f"Saved meals on {progress['date']}: {progress['meal_count']}. "
        f"Calories eaten {consumed}. Remaining {remaining}. {progress['goal_label']}."
    )
    return {
        "status": "NEEDS_CLARIFICATION",
        "reply": reply,
        "provider": "progress",
        "meal_id": None,
        "language": language,
    }


def _confirmable(value) -> str | None:
    text = str(value or "").strip().lower()
    return text if text in CONFIRM_MEAL_TYPES else None


def _expired(draft: MealDraft) -> bool:
    updated = draft.updated_at
    if updated is None:
        return False
    return timezone.now() - updated > DRAFT_TTL


def build_confirmation(meal_type, items: list) -> dict:
    preview = []
    for item in items:
        if item.get("user_food_id"):
            user_food = UserFood.objects.get(pk=item["user_food_id"])
            calculated = calculate_user_food(user_food, item["quantity"], item["unit"])
            preview.append(
                {
                    "food_code": "",
                    "user_food_id": user_food.id,
                    "food_name": calculated["food_name"],
                    "quantity": str(calculated["quantity"]),
                    "unit": calculated["unit"],
                    "provenance": "user_provided",
                    "nutrition": {
                        name: None if calculated["nutrients"].get(name) is None else str(calculated["nutrients"][name])
                        for name in NUTRIENT_FIELDS
                    },
                }
            )
            continue
        calculated = calculate_nutrition(item["food_code"], item["quantity"], item["unit"])
        preview.append(
            {
                "food_code": calculated["food_code"],
                "user_food_id": None,
                "food_name": calculated["food_name"],
                "original_name": item.get("original_query") or "",
                "quantity": str(calculated["quantity"]),
                "unit": calculated["unit"],
                "provenance": "verified",
                "nutrition": {
                    name: None if calculated["nutrients"].get(name) is None else str(calculated["nutrients"][name])
                    for name in NUTRIENT_FIELDS
                },
            }
        )
    selected = _confirmable(meal_type)
    return {"meal_type": selected, "meal_type_required": selected is None, "items": preview}


def _confirmation_result(draft: MealDraft) -> dict:
    meal_type = _confirmable(draft.meal_type)
    confirmation = build_confirmation(meal_type, draft.items)
    return {
        "status": "AWAITING_CONFIRMATION",
        "reply": "Check this meal before I log it.",
        "confirmation": confirmation,
        "provider": "draft",
        "meal_type": meal_type,
        "mentions": draft.items,
        "draft_items": draft.items,
        "meal_id": None,
    }


def _pending_confirmation_turn(state: AgentState, draft: MealDraft, text: str) -> dict:
    if _RETRY.match(text):
        return _confirmation_result(draft)
    meal_only = _MEAL_ONLY.match(text.strip())
    if meal_only:
        draft.meal_type = meal_only.group(1).lower()
        draft.status = "awaiting_confirmation"
        draft.save(update_fields=["meal_type", "status", "updated_at"])
        return _confirmation_result(draft)
    parsed = parse_quantity_reply(text)
    if parsed and not meaningful_food_query(text) and len(draft.items) == 1:
        items = copy.deepcopy(draft.items)
        items[0]["quantity"] = str(parsed["quantity"])
        if parsed.get("unit"):
            items[0]["unit"] = parsed["unit"]
        items[0]["quantity_confirmed"] = True
        items[0]["status"] = "awaiting_quantity"
        return _draft_state(_confirmable(draft.meal_type), items)
    corrected = _correction_query(text) if _CORRECTION.match(text.strip()) else ""
    if corrected and meaningful_food_query(corrected) and len(draft.items) == 1:
        item = draft.items[0]
        return _draft_state(
            _confirmable(draft.meal_type),
            [
                _fresh_item(
                    corrected,
                    quantity=item.get("quantity"),
                    unit=item.get("unit"),
                    confirmed=bool(item.get("quantity_confirmed")),
                )
            ],
        )
    return _confirmation_result(draft)


def pending_confirmation(*, user, conversation) -> dict:
    draft = MealDraft.objects.filter(user=user, conversation=conversation).first()
    if draft is not None and _expired(draft):
        draft.delete()
        draft = None
    if draft is None or draft.status != "awaiting_confirmation":
        return {"conversation_id": conversation.id, "confirmation": None}
    return {
        "conversation_id": conversation.id,
        "status": "AWAITING_CONFIRMATION",
        "confirmation": build_confirmation(draft.meal_type, draft.items),
    }


def _lock_draft(*, user, conversation) -> MealDraft | None:
    _lock_conversation({"user_id": user.id, "conversation_id": conversation.id})
    return MealDraft.objects.select_for_update().filter(user=user, conversation=conversation).first()


def update_pending_meal(*, user, conversation, meal_type=None, items=None) -> dict:
    clarification = None
    confirmation = None
    message = ""
    expired = False
    with transaction.atomic():
        draft = _lock_draft(user=user, conversation=conversation)
        if draft is None or draft.status != "awaiting_confirmation":
            raise NotFound("There is no meal waiting to be logged.")
        if _expired(draft):
            draft.delete()
            expired = True
        else:
            next_type = _confirmable(draft.meal_type) or ""
            if meal_type is not None:
                selected = _confirmable(meal_type)
                if selected is None:
                    raise ValidationError({"meal_type": ["Choose breakfast, lunch, dinner, or snack."]})
                next_type = selected
            next_items = copy.deepcopy(draft.items)
            state = {"user_id": user.id, "conversation_id": conversation.id, "text": ""}
            if items is not None:
                if not isinstance(items, list) or not items:
                    raise ValidationError({"items": ["Describe the food and quantity."]})
                built = []
                for raw in items:
                    if not isinstance(raw, dict):
                        raise ValidationError({"items": ["Describe the food and quantity."]})
                    built.append(
                        _item_from_mention(
                            {
                                "food_query": str(raw.get("food_query") or raw.get("food_name") or "").strip(),
                                "quantity": raw.get("quantity"),
                                "unit": raw.get("unit"),
                            }
                        )
                    )
                resolved = [_resolve_draft_item(state, item) for item in built]
                blocking = next((item for item in resolved if item["status"] != "ready"), None)
                if blocking is not None:
                    _save_draft(state, next_type, resolved, blocking["status"])
                    clarification = blocking.get("reply") or "I need a bit more detail."
                else:
                    next_items = resolved
            if clarification is None:
                confirmation = build_confirmation(next_type, next_items)
                _save_draft(state, next_type, next_items, "awaiting_confirmation")
                if items is not None:
                    message = "Updated the meal. Check it again before I log it."
    if expired:
        raise ValidationError("This meal confirmation expired. Describe the meal again.")
    if clarification is not None:
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=clarification,
            input_type=Message.InputType.TEXT,
        )
        return {
            "status": "NEEDS_CLARIFICATION",
            "message": clarification,
            "meal_id": None,
            "confirmation": None,
            "conversation_id": conversation.id,
        }
    if message:
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=message,
            input_type=Message.InputType.TEXT,
        )
    return {
        "status": "AWAITING_CONFIRMATION",
        "message": message,
        "meal_id": None,
        "confirmation": confirmation,
        "conversation_id": conversation.id,
    }


def cancel_pending_meal(*, user, conversation) -> dict:
    with transaction.atomic():
        draft = _lock_draft(user=user, conversation=conversation)
        if draft is not None:
            draft.delete()
    reply = "Okay, I won't log that meal."
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=reply,
        input_type=Message.InputType.TEXT,
    )
    return {
        "status": "NEEDS_CLARIFICATION",
        "message": reply,
        "meal_id": None,
        "confirmation": None,
        "conversation_id": conversation.id,
    }


def confirm_pending_meal(*, user, conversation, meal_type: str) -> dict:
    selected = _confirmable(meal_type)
    if selected is None:
        raise ValidationError({"meal_type": ["Choose breakfast, lunch, dinner, or snack."]})
    missing = False
    expired = False
    meal = None
    reply = ""
    celebration = None
    with transaction.atomic():
        draft = _lock_draft(user=user, conversation=conversation)
        if draft is None or draft.status != "awaiting_confirmation":
            missing = True
        elif _expired(draft):
            draft.delete()
            expired = True
        else:
            if not draft.items or any(
                item.get("status") != "ready" or not (item.get("food_code") or item.get("user_food_id")) for item in draft.items
            ):
                raise ValidationError("This meal still needs a food and a quantity.")
            prepared = []
            names = []
            for item in draft.items:
                try:
                    if item.get("user_food_id"):
                        user_food = UserFood.objects.get(pk=item["user_food_id"], user=user)
                        calculated = calculate_user_food(user_food, item["quantity"], item["unit"])
                        prepared.append(
                            {
                                "user_food_id": user_food.id,
                                "quantity": calculated["quantity"],
                                "unit": calculated["unit"],
                                "input_source": "text",
                                "confidence": None,
                            }
                        )
                        names.append(f"{calculated['quantity']} {calculated['unit']} {calculated['food_name']}")
                    else:
                        calculated = calculate_nutrition(item["food_code"], item["quantity"], item["unit"])
                        prepared.append(
                            {
                                "food_code": calculated["food_code"],
                                "quantity": calculated["quantity"],
                                "unit": calculated["unit"],
                                "input_source": "text",
                                "confidence": None,
                            }
                        )
                        names.append(f"{calculated['quantity']} {calculated['unit']} {calculated['food_name']}")
                except NutritionError as exc:
                    raise ValidationError(str(exc)) from exc
            before = day_goal_status(user)["goal_status"]
            meal = create_food_log(user=user, items=prepared, meal_type=selected, input_source="text")
            from apps.meals.plan_services import mark_slot_logged

            mark_slot_logged(user, meal)
            draft.delete()
            progress = get_daily_progress(user)
            celebration = record_new_achievement(
                user=user,
                day=meal.timestamp.date(),
                before=before,
                after=day_goal_status(user, meal.timestamp.date())["goal_status"],
                meal=meal,
            )
            reply = f"Logged {', '.join(names)}."
            remaining = progress["remaining"]
            if remaining and remaining.get("calories") is not None:
                reply = f"{reply} About {remaining['calories']} kcal remains for today."
            reply = localize_reply(reply, _preferred_language(user.id))
            AgentAction.objects.create(
                conversation=conversation,
                action_type="persist",
                tool_name="create_food_log",
                tool_input={
                    "items": [
                        {
                            "food_code": item.get("food_code") or "",
                            "quantity": str(item["quantity"]),
                            "unit": item["unit"],
                        }
                        for item in prepared
                    ]
                },
                tool_output={"meal_id": meal.id},
                status="ok",
            )
            Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                content=reply,
                input_type=Message.InputType.TEXT,
            )
    if missing:
        raise NotFound("There is no meal waiting to be logged.")
    if expired:
        raise ValidationError("This meal confirmation expired. Describe the meal again.")
    return {
        "status": "SUCCESS",
        "message": reply,
        "meal_id": meal.id,
        "conversation_id": conversation.id,
        "confirmation": None,
        "celebration": celebration,
    }
