"""LangGraph workflow for one text meal message.

The signed-in user id is placed in the state by the view. Nodes do not read a
user id from the model output. A meal is saved only after calculation succeeds.
"""

from typing import TypedDict

from django.contrib.auth import get_user_model
from langgraph.graph import END, START, StateGraph
from rest_framework.exceptions import APIException

from apps.conversations.models import AgentAction, Conversation
from apps.meals.services import create_food_log
from apps.nutrition.calculation import NutritionError, calculate_nutrition
from apps.nutrition.search import resolve_food
from apps.progress.services import get_daily_progress

from .providers import ProviderError, get_provider

User = get_user_model()


class AgentState(TypedDict, total=False):
    user_id: int
    conversation_id: int
    text: str
    provider: str
    meal_type: str | None
    mentions: list
    resolved: list
    status: str
    reply: str
    meal_id: int | None


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


def extract_node(state: AgentState) -> dict:
    provider = get_provider()
    try:
        extracted = provider.extract(state["text"])
    except ProviderError as exc:
        _record(state, "extract", provider.name, {"text": state["text"]}, {"error": str(exc)}, "error")
        return {"status": "ERROR", "reply": str(exc), "mentions": [], "provider": provider.name}
    _record(state, "extract", provider.name, {"text": state["text"]}, extracted, "ok")
    return {
        "provider": extracted["provider"],
        "meal_type": extracted["meal_type"],
        "mentions": extracted["items"],
        "status": "NEEDS_CLARIFICATION" if not extracted["items"] else "",
        "reply": "Tell me the food and how much of it you ate." if not extracted["items"] else "",
    }


def resolve_node(state: AgentState) -> dict:
    resolved = []
    for mention in state.get("mentions") or []:
        resolved.append(_resolve_mention(state, mention))
    blocking = next((item for item in resolved if item["status"] != "ready"), None)
    if blocking is None:
        return {"resolved": resolved, "status": ""}
    return {
        "resolved": resolved,
        "status": "NEEDS_CLARIFICATION",
        "reply": blocking["reply"],
    }


def persist_node(state: AgentState) -> dict:
    user = User.objects.get(pk=state["user_id"])
    items = []
    for item in state["resolved"]:
        items.append(
            {
                "food_code": item["food_code"],
                "quantity": item["quantity"],
                "unit": item["unit"],
                "input_source": "text",
                "confidence": None,
            }
        )
    try:
        meal = create_food_log(
            user=user,
            items=items,
            meal_type=state.get("meal_type") or "unspecified",
            input_source="text",
        )
    except APIException as exc:
        _record(state, "persist", "create_food_log", {"items": items}, {"error": str(exc)}, "error")
        return {"status": "ERROR", "reply": str(exc), "meal_id": None}
    _record(
        state,
        "persist",
        "create_food_log",
        {"items": [{"food_code": item["food_code"], "quantity": str(item["quantity"]), "unit": item["unit"]} for item in items]},
        {"meal_id": meal.id},
        "ok",
    )
    progress = get_daily_progress(user)
    names = ", ".join(f"{item['quantity']} {item['unit']} {item['food_name']}" for item in state["resolved"])
    reply = f"Logged {names}."
    remaining = progress["remaining"]
    if remaining and remaining.get("calories") is not None:
        reply = f"{reply} About {remaining['calories']} kcal remains for today."
    return {"status": "SUCCESS", "reply": reply, "meal_id": meal.id}


def respond_node(state: AgentState) -> dict:
    return {"status": state.get("status") or "NEEDS_CLARIFICATION", "reply": state.get("reply") or "I need a bit more detail."}


def _resolve_mention(state: AgentState, mention: dict) -> dict:
    query = str(mention.get("food_query") or "").strip()
    resolution = _resolve_query(query)
    _record(state, "resolve", "resolve_food", {"query": query}, {"status": resolution["status"]}, "ok")
    if resolution["status"] == "ambiguous":
        names = ", ".join(food.food_name for food in resolution["foods"])
        return {"status": "ambiguous", "reply": f"Which food did you mean? {names}."}
    if resolution["status"] != "resolved":
        return {"status": "not_found", "reply": f"I couldn't find {query} in the verified foods."}
    food = resolution["food"]
    if mention.get("quantity") in (None, ""):
        return {"status": "missing_quantity", "reply": f"How much {food.food_name} did you eat?"}
    unit = mention.get("unit") or _inferred_unit(query, food.serving_unit)
    if not unit:
        verified = food.serving_unit or "a verified serving"
        return {
            "status": "missing_unit",
            "reply": f"How much {food.food_name} did you eat? Grams, kilograms, or {verified} are the choices I can use.",
        }
    try:
        calculate_nutrition(food.food_code, mention["quantity"], unit)
    except NutritionError as exc:
        _record(state, "validate", "calculate_nutrition", {"food_code": food.food_code, "unit": unit}, {"code": exc.code}, "error")
        return {"status": exc.code, "reply": str(exc)}
    return {
        "status": "ready",
        "food_code": food.food_code,
        "food_name": food.food_name,
        "quantity": str(mention["quantity"]),
        "unit": unit,
        "reply": "",
    }


def _resolve_query(query: str) -> dict:
    last = {"status": "not_found", "foods": []}
    for candidate in _query_candidates(query):
        last = resolve_food(candidate, semantic=False)
        if last["status"] != "not_found":
            return last
    return resolve_food(_singular(query), semantic=True)


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
    if state.get("status") in {"ERROR", "NEEDS_CLARIFICATION"}:
        return "respond"
    return "resolve"


def _after_resolve(state: AgentState) -> str:
    if state.get("status") == "NEEDS_CLARIFICATION":
        return "respond"
    return "persist"


def _build():
    graph = StateGraph(AgentState)
    graph.add_node("extract", extract_node)
    graph.add_node("resolve", resolve_node)
    graph.add_node("persist", persist_node)
    graph.add_node("respond", respond_node)
    graph.add_edge(START, "extract")
    graph.add_conditional_edges("extract", _after_extract, {"resolve": "resolve", "respond": "respond"})
    graph.add_conditional_edges("resolve", _after_resolve, {"persist": "persist", "respond": "respond"})
    graph.add_edge("persist", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


_graph = _build()
