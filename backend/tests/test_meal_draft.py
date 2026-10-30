import threading
from decimal import Decimal
from pathlib import Path

import pytest
from rest_framework.exceptions import APIException

from apps.agent.views import _execute_turn, join_or_run_turn
from apps.conversations.models import AgentAction, Conversation, MealDraft, Message
from apps.meals.models import Meal
from apps.nutrition.search import resolve_food
from tests.test_application import _auth
from tests.test_nutrition import _row, _write

def _load(tmp_path: Path):
    path = tmp_path / "foods.xlsx"
    _write(
        path,
        [
            _row(food_code="UPMA-S", food_name="Semolina upma", energy_kcal=100),
            _row(food_code="UPMA-V", food_name="Vegetable upma", energy_kcal=90),
            _row(food_code="RICE-B", food_name="Brown rice", energy_kcal=130),
            _row(food_code="RICE-W", food_name="White rice", energy_kcal=130),
            _row(
                food_code="IDLI",
                food_name="Idli",
                energy_kcal=100,
                servings_unit="piece",
                unit_serving_energy_kcal=40,
            ),
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


def _confirm(api_client, conversation_id, meal_type="breakfast"):
    response = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": conversation_id, "meal_type": meal_type},
        format="json",
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["meal_id"]
    return body


@pytest.mark.django_db
def test_upma_clarification_keeps_the_selected_food_until_it_is_saved(api_client, make_user, tmp_path, monkeypatch):
    _load(tmp_path)
    user = make_user(email="upma@example.com")
    _auth(api_client, user)

    opening = _chat(api_client, "I ate one plate Upma for breakfast.")
    assert opening["status"] == "NEEDS_CLARIFICATION"
    assert "Semolina upma" in opening["message"]
    assert "Vegetable upma" in opening["message"]
    assert opening["meal_id"] is None
    assert Meal.objects.filter(user=user).count() == 0
    draft = MealDraft.objects.get(conversation_id=opening["conversation_id"], user=user)
    assert draft.meal_type == "breakfast"
    assert draft.status == "awaiting_choice"
    assert draft.items[0]["food_code"] is None
    assert {candidate["food_code"] for candidate in draft.items[0]["candidates"]} == {"UPMA-S", "UPMA-V"}
    extracts = AgentAction.objects.filter(conversation_id=opening["conversation_id"], action_type="extract").count()

    def fail_search(*args, **kwargs):
        raise AssertionError("a clarification must not start a new food search")

    monkeypatch.setattr("apps.agent.workflow.resolve_food_mention", fail_search)
    monkeypatch.setattr("apps.agent.workflow.get_provider", fail_search)
    choice = _chat(api_client, "Rava upma.", opening["conversation_id"])
    assert choice["status"] == "NEEDS_CLARIFICATION"
    assert choice["message"] == "How much Semolina upma did you eat?"
    assert Meal.objects.filter(user=user).count() == 0
    draft.refresh_from_db()
    assert draft.status == "awaiting_quantity"
    assert draft.meal_type == "breakfast"
    assert draft.items[0]["food_code"] == "UPMA-S"
    assert draft.items[0]["food_name"] == "Semolina upma"
    assert AgentAction.objects.filter(conversation_id=opening["conversation_id"], action_type="extract").count() == extracts

    pending = _chat(api_client, "1 plate about 350g.", opening["conversation_id"])
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert pending["meal_id"] is None
    assert pending["confirmation"]["meal_type"] == "breakfast"
    assert pending["confirmation"]["items"][0]["food_name"] == "Semolina upma"
    assert Decimal(pending["confirmation"]["items"][0]["quantity"]) == Decimal("350")
    assert pending["confirmation"]["items"][0]["unit"] == "g"
    assert Decimal(pending["confirmation"]["items"][0]["nutrition"]["energy_kcal"]) == Decimal("350")
    assert Meal.objects.filter(user=user).count() == 0
    assert MealDraft.objects.filter(conversation_id=opening["conversation_id"], status="awaiting_confirmation").exists()

    logged = _confirm(api_client, opening["conversation_id"], "breakfast")
    assert logged["message"].startswith("Logged 350 g Semolina upma.")
    meal = Meal.objects.get(user=user)
    assert meal.id == logged["meal_id"]
    assert meal.meal_type == "breakfast"
    item = meal.items.get()
    assert item.food.food_code == "UPMA-S"
    assert item.quantity == Decimal("350")
    assert item.unit == "g"
    assert Decimal(item.nutrition_snapshot["energy_kcal"]) == Decimal("350")
    assert not MealDraft.objects.filter(conversation_id=opening["conversation_id"]).exists()
    assert Message.objects.filter(conversation_id=opening["conversation_id"], role="user", content="1 plate about 350g.").count() == 1
    assert Message.objects.filter(conversation_id=opening["conversation_id"], role="assistant", content__startswith="Logged").count() == 1
    repeated = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": opening["conversation_id"], "meal_type": "breakfast"},
        format="json",
    )
    assert repeated.status_code == 404
    assert Meal.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_quantity_reply_does_not_replace_the_offered_foods(api_client, make_user, tmp_path, monkeypatch):
    _load(tmp_path)
    user = make_user(email="quantity@example.com")
    _auth(api_client, user)
    opening = _chat(api_client, "I ate one plate Upma for breakfast.")
    before = MealDraft.objects.get(conversation_id=opening["conversation_id"]).items

    monkeypatch.setattr(
        "apps.nutrition.search.similar_foods",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("semantic search should not run")),
    )
    monkeypatch.setattr(
        "apps.agent.workflow.resolve_food_mention",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("quantity reply should not search")),
    )
    reply = _chat(api_client, "350g", opening["conversation_id"])
    assert reply["status"] == "NEEDS_CLARIFICATION"
    assert "Semolina upma" in reply["message"]
    assert "Vegetable upma" in reply["message"]
    assert Meal.objects.filter(user=user).count() == 0
    assert MealDraft.objects.get(conversation_id=opening["conversation_id"]).items == before

    unrelated = resolve_food("1 plate about 350g", semantic=True)
    assert unrelated["status"] == "not_found"


@pytest.mark.django_db
def test_named_choice_resolves_an_ambiguous_food_and_keeps_its_quantity(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="rice@example.com")
    _auth(api_client, user)
    opening = _chat(api_client, "I had 250 grams of rice")
    assert opening["status"] == "NEEDS_CLARIFICATION"
    assert "Brown rice" in opening["message"]
    assert "White rice" in opening["message"]
    assert Meal.objects.filter(user=user).count() == 0

    pending = _chat(api_client, "White rice", opening["conversation_id"])
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert pending["confirmation"]["meal_type"] is None
    assert Meal.objects.filter(user=user).count() == 0
    _confirm(api_client, opening["conversation_id"], "lunch")
    item = Meal.objects.get(user=user).items.get()
    assert item.food.food_code == "RICE-W"
    assert item.quantity == Decimal("250")
    assert item.unit == "g"
    assert Meal.objects.get(user=user).meal_type == "lunch"
    assert not MealDraft.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_failed_persistence_keeps_the_draft_for_a_retry(api_client, make_user, tmp_path, monkeypatch):
    _load(tmp_path)
    user = make_user(email="retry@example.com")
    _auth(api_client, user)
    opening = _chat(api_client, "I ate one plate Upma for breakfast.")
    _chat(api_client, "Rava upma.", opening["conversation_id"])

    def fail_save(*args, **kwargs):
        error = APIException("The meal could not be saved.")
        error.status_code = 400
        raise error

    pending = _chat(api_client, "1 plate about 350g.", opening["conversation_id"])
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert Meal.objects.filter(user=user).count() == 0
    monkeypatch.setattr("apps.agent.workflow.create_food_log", fail_save)
    failed = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": opening["conversation_id"], "meal_type": "breakfast"},
        format="json",
    )
    assert failed.status_code == 400
    assert "Logged" not in failed.json()["error"]["message"]
    assert Meal.objects.filter(user=user).count() == 0
    draft = MealDraft.objects.get(conversation_id=opening["conversation_id"])
    assert draft.items[0]["food_code"] == "UPMA-S"
    assert draft.status == "awaiting_confirmation"
    assert Decimal(draft.items[0]["quantity"]) == Decimal("350")

    monkeypatch.undo()
    retry = _chat(api_client, "try again", opening["conversation_id"])
    assert retry["status"] == "AWAITING_CONFIRMATION"
    assert Meal.objects.filter(user=user).count() == 0
    logged = _confirm(api_client, opening["conversation_id"], "breakfast")
    assert logged["status"] == "SUCCESS"
    assert Meal.objects.filter(user=user).count() == 1
    assert not MealDraft.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_pieces_and_unclear_amounts_stay_on_the_pending_food(api_client, make_user, tmp_path, monkeypatch):
    _load(tmp_path)
    user = make_user(email="pieces@example.com")
    _auth(api_client, user)
    opening = _chat(api_client, "I ate idli")
    assert opening["message"] == "How much Idli did you eat?"
    monkeypatch.setattr(
        "apps.agent.workflow.resolve_food_mention",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("quantity reply should not search")),
    )

    unclear = _chat(api_client, "some", opening["conversation_id"])
    assert unclear["status"] == "NEEDS_CLARIFICATION"
    assert unclear["message"] == "How much Idli did you eat?"
    assert MealDraft.objects.get(conversation_id=opening["conversation_id"]).items[0]["food_code"] == "IDLI"
    assert Meal.objects.filter(user=user).count() == 0

    plate = _chat(api_client, "1 plate", opening["conversation_id"])
    assert plate["status"] == "NEEDS_CLARIFICATION"
    assert "plate" in plate["message"]
    assert "Logged" not in plate["message"]
    assert Meal.objects.filter(user=user).count() == 0
    assert MealDraft.objects.get(conversation_id=opening["conversation_id"]).items[0]["food_code"] == "IDLI"

    pending = _chat(api_client, "2 pieces", opening["conversation_id"])
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert Meal.objects.filter(user=user).count() == 0
    _confirm(api_client, opening["conversation_id"], "dinner")
    item = Meal.objects.get(user=user).items.get()
    assert item.food.food_code == "IDLI"
    assert item.quantity == Decimal("2")
    assert item.unit == "piece"
    assert Decimal(item.nutrition_snapshot["energy_kcal"]) == Decimal("80")


@pytest.mark.django_db
def test_one_clarification_does_not_drop_an_already_resolved_food(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="both@example.com")
    _auth(api_client, user)
    opening = _chat(api_client, "I ate upma and 2 pieces of idli for breakfast")
    assert opening["status"] == "NEEDS_CLARIFICATION"
    assert "Semolina upma" in opening["message"]
    draft = MealDraft.objects.get(conversation_id=opening["conversation_id"])
    assert [item["food_code"] for item in draft.items] == [None, "IDLI"]
    assert draft.items[1]["status"] == "ready"

    choice = _chat(api_client, "Rava upma.", opening["conversation_id"])
    assert choice["message"] == "How much Semolina upma did you eat?"
    draft.refresh_from_db()
    assert draft.items[1]["food_code"] == "IDLI"
    assert draft.items[1]["status"] == "ready"

    pending = _chat(api_client, "350g", opening["conversation_id"])
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert Meal.objects.filter(user=user).count() == 0
    _confirm(api_client, opening["conversation_id"], "breakfast")
    meal = Meal.objects.get(user=user)
    codes = list(meal.items.order_by("id").values_list("food__food_code", flat=True))
    assert codes == ["UPMA-S", "IDLI"]
    assert meal.meal_type == "breakfast"


@pytest.mark.django_db
def test_cancel_and_a_repeated_quantity_do_not_save_twice(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="cancel@example.com")
    _auth(api_client, user)
    opening = _chat(api_client, "I ate one plate Upma for breakfast.")
    cancelled = _chat(api_client, "cancel", opening["conversation_id"])
    assert cancelled["meal_id"] is None
    assert "won't log" in cancelled["message"]
    assert not MealDraft.objects.filter(user=user).exists()
    assert Meal.objects.filter(user=user).count() == 0

    again = _chat(api_client, "I ate one plate Upma for breakfast.", opening["conversation_id"])
    _chat(api_client, "Rava upma.", again["conversation_id"])
    pending = _chat(api_client, "1 plate about 350g.", again["conversation_id"])
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert Meal.objects.filter(user=user).count() == 0
    repeated = _chat(api_client, "1 plate about 350g.", again["conversation_id"])
    assert repeated["status"] == "AWAITING_CONFIRMATION"
    assert repeated["meal_id"] is None
    assert Meal.objects.filter(user=user).count() == 0
    _confirm(api_client, again["conversation_id"], "breakfast")
    second = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": again["conversation_id"], "meal_type": "breakfast"},
        format="json",
    )
    assert second.status_code == 404
    assert Meal.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_chat_failure_shows_one_error_and_does_not_save_a_meal(api_client, make_user, monkeypatch):
    user = make_user(email="chat-fail@example.com")
    _auth(api_client, user)

    def explode(*args, **kwargs):
        raise RuntimeError("provider exploded sk-or-v1-secretvalue")

    monkeypatch.setattr("apps.agent.views.run_text_turn", explode)
    failed = _chat(api_client, "Hi")
    assert failed["status"] == "ERROR"
    assert failed["meal_id"] is None
    assert "secretvalue" not in failed["message"]
    assert "sk-or" not in failed["message"]
    assert Message.objects.filter(conversation_id=failed["conversation_id"], role="user").count() == 1
    assert Message.objects.filter(conversation_id=failed["conversation_id"], role="assistant").count() == 1
    assert Meal.objects.filter(user=user).count() == 0


@pytest.mark.django_db(transaction=True)
def test_duplicate_quantity_submission_logs_one_meal(make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="duplicate@example.com")
    conversation = Conversation.objects.create(user=user)
    from apps.agent.workflow import run_text_turn

    opening = run_text_turn(user_id=user.id, conversation_id=conversation.id, text="I ate one plate Upma for breakfast.")
    assert opening["status"] == "NEEDS_CLARIFICATION"
    chosen = run_text_turn(user_id=user.id, conversation_id=conversation.id, text="Rava upma.")
    assert chosen["status"] == "NEEDS_CLARIFICATION"
    assert MealDraft.objects.filter(conversation=conversation).exists()

    started = threading.Event()
    release = threading.Event()
    results = [None, None]

    def run():
        started.set()
        release.wait(timeout=2)
        return _execute_turn(user, conversation, "1 plate about 350g.", Message.InputType.TEXT)

    def owner():
        results[0] = join_or_run_turn(conversation.id, "1 plate about 350g.", run)

    def waiter():
        assert started.wait(timeout=2)
        results[1] = join_or_run_turn(conversation.id, "1 plate about 350g.", run)

    first = threading.Thread(target=owner)
    second = threading.Thread(target=waiter)
    first.start()
    second.start()
    assert started.wait(timeout=2)
    release.set()
    first.join(timeout=10)
    second.join(timeout=10)
    assert results[0]["status"] == "AWAITING_CONFIRMATION"
    assert results[1]["status"] == "AWAITING_CONFIRMATION"
    assert results[0]["meal_id"] is None
    assert Meal.objects.filter(user=user).count() == 0

    from apps.agent.workflow import confirm_pending_meal
    from rest_framework.exceptions import NotFound

    saved = []
    blocked = []

    def confirm():
        try:
            saved.append(confirm_pending_meal(user=user, conversation=conversation, meal_type="breakfast"))
        except NotFound as exc:
            blocked.append(exc)

    first_confirm = threading.Thread(target=confirm)
    second_confirm = threading.Thread(target=confirm)
    first_confirm.start()
    second_confirm.start()
    first_confirm.join(timeout=10)
    second_confirm.join(timeout=10)
    assert len(saved) == 1
    assert saved[0]["status"] == "SUCCESS"
    assert len(blocked) == 1
    assert Meal.objects.filter(user=user).count() == 1
