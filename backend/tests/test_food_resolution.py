from decimal import Decimal

import pytest

from apps.agent.providers import RulesProvider, _extract_payload
from apps.conversations.models import AgentAction, Conversation, MealDraft, Message
from apps.meals.models import Meal
from apps.nutrition.models import Food
from apps.nutrition.search import resolve_food
from tests.test_application import _auth
from tests.test_nutrition import _row, _write


def _foods(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(
        path,
        [
            _row(food_code="ROTI", food_name="Chapati/Roti", energy_kcal=250),
            _row(food_code="MILK-C", food_name="Cow milk", energy_kcal=60),
            _row(food_code="MILK-B", food_name="Buffalo milk", energy_kcal=90),
            _row(food_code="UPMA-S", food_name="Semolina upma", energy_kcal=100),
            _row(food_code="UPMA-V", food_name="Vegetable upma", energy_kcal=90),
            _row(food_code="MANGO", food_name="Mango", energy_kcal=60),
        ],
    )
    from apps.nutrition.ingestion import load_nutrition

    load_nutrition(path)


def _chat(api_client, message, conversation_id=None):
    payload = {"message": message}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    response = api_client.post("/api/agent/chat/", payload, format="json")
    assert response.status_code == 200, response.content
    return response.json()


@pytest.mark.django_db
def test_a_model_meal_type_is_ignored_unless_the_user_named_it(api_client, make_user, tmp_path, monkeypatch):
    _foods(tmp_path)
    user = make_user(email="no-guess-category@example.com")
    _auth(api_client, user)

    class Guessing(RulesProvider):
        def extract(self, text):
            result = super().extract(text)
            result["meal_type"] = "breakfast"
            return result

    monkeypatch.setattr("apps.agent.workflow.get_provider", lambda: Guessing())
    pending = _chat(api_client, "I ate 100 grams of chapati")
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert pending["confirmation"]["meal_type"] is None
    assert pending["confirmation"]["meal_type_required"] is True
    blocked = api_client.post("/api/agent/confirm/", {"conversation_id": pending["conversation_id"]}, format="json")
    assert blocked.status_code == 400
    assert Meal.objects.filter(user=user).count() == 0


def test_sentence_is_reduced_to_the_food_name_before_search():
    rules = RulesProvider().extract("I ate 1 chapati")
    assert rules["items"][0]["food_query"] == "chapati"
    assert rules["items"][0]["quantity"] == "1"
    milk = RulesProvider().extract("I had milk")
    assert milk["items"][0]["food_query"] == "milk"
    upma = RulesProvider().extract("I ate one plate of upma")
    assert upma["items"][0]["food_query"] == "upma"
    assert "plate" not in upma["items"][0]["food_query"]
    echoed = _extract_payload(
        "openrouter",
        {"meal_type": None, "items": [{"food_query": "I ate 1 chapati", "quantity": None, "unit": None}]},
    )
    assert echoed["items"][0]["food_query"] == "chapati"
    assert echoed["items"][0]["quantity"] == "1"


@pytest.mark.django_db
def test_chapati_milk_and_upma_use_the_food_name_not_the_sentence(api_client, make_user, tmp_path, monkeypatch):
    _foods(tmp_path)
    user = make_user(email="resolve-food@example.com")
    _auth(api_client, user)

    chapati = _chat(api_client, "I ate 1 chapati")
    assert "Chapati/Roti" in chapati["message"]
    assert "Mango" not in chapati["message"]
    assert "I ate 1 chapati" not in chapati["message"]
    draft = MealDraft.objects.get(conversation_id=chapati["conversation_id"])
    assert draft.items[0]["food_code"] == "ROTI"
    assert Meal.objects.filter(user=user).count() == 0
    searched = AgentAction.objects.filter(conversation_id=chapati["conversation_id"], action_type="resolve").latest("id")
    assert searched.tool_input["query"].casefold() == "chapati"

    milk = _chat(api_client, "I had milk")
    assert "Cow milk" in milk["message"]
    assert "Buffalo milk" in milk["message"]
    assert "Mango" not in milk["message"]
    assert Meal.objects.filter(user=user).count() == 0

    def unrelated(*args, **kwargs):
        return list(Food.objects.filter(food_code="MANGO"))

    monkeypatch.setattr("apps.nutrition.search.similar_foods", unrelated)
    missing = _chat(api_client, "I ate 1 chapati made of nothing")
    assert "Mango" not in missing["message"]
    assert missing["meal_id"] is None


@pytest.mark.django_db
def test_selected_upma_keeps_the_later_quantity(api_client, make_user, tmp_path, monkeypatch):
    _foods(tmp_path)
    user = make_user(email="upma-follow@example.com")
    _auth(api_client, user)
    opening = _chat(api_client, "I ate one plate of upma")
    assert "Semolina upma" in opening["message"]
    assert "Vegetable upma" in opening["message"]
    monkeypatch.setattr(
        "apps.agent.workflow.resolve_food_mention",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("the quantity reply must not search again")),
    )
    choice = _chat(api_client, "Rava upma", opening["conversation_id"])
    assert choice["message"] == "How much Semolina upma did you eat?"
    pending = _chat(api_client, "1 plate about 350 g", opening["conversation_id"])
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert pending["confirmation"]["items"][0]["food_code"] == "UPMA-S"
    assert pending["confirmation"]["items"][0]["quantity"] in {"350", "350.0"}
    assert pending["confirmation"]["items"][0]["unit"] == "g"
    assert Meal.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_confirmation_keeps_calorie_precision_for_the_client_to_round(api_client, make_user, tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(path, [_row(food_code="ROTI", food_name="Chapati/Roti", energy_kcal=68.9)])
    from apps.nutrition.ingestion import load_nutrition

    load_nutrition(path)
    user = make_user(email="kcal-precision@example.com")
    _auth(api_client, user)
    pending = _chat(api_client, "I ate 100 grams of chapati for breakfast")
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert Decimal(pending["confirmation"]["items"][0]["nutrition"]["energy_kcal"]) == Decimal("68.9")


@pytest.mark.django_db
def test_greetings_do_not_search_the_food_dataset(api_client, make_user, monkeypatch):
    user = make_user(email="greeting@example.com")
    _auth(api_client, user)

    def fail_search(*args, **kwargs):
        raise AssertionError("a greeting must not search foods")

    monkeypatch.setattr("apps.agent.workflow.resolve_food_mention", fail_search)
    monkeypatch.setattr("apps.agent.workflow.get_provider", fail_search)
    for message, expected in (
        ("hi", "Hello"),
        ("good morning", "Good morning"),
        ("thanks", "You're welcome"),
    ):
        reply = _chat(api_client, message)
        assert reply["meal_id"] is None
        assert expected in reply["message"]
        assert "Which food did you mean" not in reply["message"]
        assert AgentAction.objects.filter(conversation_id=reply["conversation_id"], action_type="resolve").count() == 0
    assert Meal.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_short_text_does_not_match_names_that_merely_contain_those_letters(tmp_path):
    _foods(tmp_path)
    assert resolve_food("hi")["status"] == "not_found"


@pytest.mark.django_db
def test_ambiguous_clarification_lists_at_most_three_relevant_foods(api_client, make_user, tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(
        path,
        [
            _row(food_code="U1", food_name="Semolina upma"),
            _row(food_code="U2", food_name="Vegetable upma"),
            _row(food_code="U3", food_name="Rava upma"),
            _row(food_code="U4", food_name="Onion upma"),
            _row(food_code="MANGO", food_name="Mango"),
        ],
    )
    from apps.nutrition.ingestion import load_nutrition

    load_nutrition(path)
    user = make_user(email="few-choices@example.com")
    _auth(api_client, user)
    reply = _chat(api_client, "I ate upma")
    assert reply["status"] == "NEEDS_CLARIFICATION"
    assert "Which food did you mean" in reply["message"]
    assert reply["message"].count(",") <= 2
    assert "Mango" not in reply["message"]
    assert "upma" in reply["message"].casefold()
    assert Meal.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_catalogue_dumps_are_hidden_without_removing_saved_meals(api_client, make_user):
    user = make_user(email="history@example.com")
    _auth(api_client, user)
    meal = Meal.objects.create(user=user, meal_type="lunch")
    conversation = Conversation.objects.create(user=user)
    Message.objects.create(conversation=conversation, role="user", content="I ate 1 chapati")
    Message.objects.create(
        conversation=conversation,
        role="assistant",
        content="Which food did you mean? Afghani chicken, Almond cardamom cake, Banana chips, Besan bathua chilla.",
    )
    Message.objects.create(conversation=conversation, role="assistant", content="Hello. What did you eat?")
    detail = api_client.get(f"/api/conversations/{conversation.id}/")
    assert detail.status_code == 200
    contents = [message["content"] for message in detail.json()["messages"]]
    assert contents == ["I ate 1 chapati", "Hello. What did you eat?"]
    assert api_client.get(f"/api/meals/{meal.id}/").status_code == 200
