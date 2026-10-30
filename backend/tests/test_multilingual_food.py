from decimal import Decimal

import pytest

from apps.agent.extract import extract_mentions
from apps.agent.providers import RulesProvider, _extract_payload, parse_quantity_reply
from apps.conversations.models import MealDraft
from apps.meals.models import Meal
from apps.nutrition.aliases import ensure_verified_aliases
from apps.nutrition.calculation import calculate_nutrition
from apps.nutrition.models import Food, FoodAlias, FoodEmbedding
from apps.nutrition.resolution import resolve_food_mention
from apps.nutrition.search import resolve_food
from tests.test_application import _auth
from tests.test_meal_draft import _chat, _confirm
from tests.test_nutrition import _row, _write


def _load(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(
        path,
        [
            _row(
                food_code="IDLI",
                food_name="Idli",
                energy_kcal=100,
                servings_unit="piece",
                unit_serving_energy_kcal=40,
            ),
            _row(food_code="UPMA-S", food_name="Semolina upma", energy_kcal=100),
            _row(food_code="UPMA-V", food_name="Vegetable upma", energy_kcal=90),
            _row(food_code="ROTI", food_name="Chapati/Roti", energy_kcal=250),
            _row(food_code="SAMBAR", food_name="Sambar", energy_kcal=50),
            _row(food_code="MANGO", food_name="Mango", energy_kcal=60),
        ],
    )
    from apps.nutrition.ingestion import load_nutrition

    load_nutrition(path)
    ensure_verified_aliases()
    FoodAlias.objects.get_or_create(
        food=Food.objects.get(food_code="UPMA-S"),
        language="en",
        normalized_alias="rava upma",
        defaults={"alias_text": "rava upma", "source": "curated", "verified": True},
    )


@pytest.mark.django_db
def test_kannada_identifies_idli_and_keeps_quantity(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="kn-idli@example.com")
    _auth(api_client, user)
    extracted = extract_mentions("ನಾನು ಎರಡು ಇಡ್ಲಿ ತಿಂದೆ.")
    assert extracted["items"][0]["food_query"]
    assert extracted["items"][0]["quantity"] == "2"
    pending = _chat(api_client, "ನಾನು ಎರಡು ಇಡ್ಲಿ ತಿಂದೆ.")
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert pending["confirmation"]["items"][0]["food_code"] == "IDLI"
    assert pending["confirmation"]["items"][0]["quantity"] in {"2", "2.0"}
    assert pending["original_text"] == "ನಾನು ಎರಡು ಇಡ್ಲಿ ತಿಂದೆ."
    assert Meal.objects.filter(user=user).count() == 0
    saved = _confirm(api_client, pending["conversation_id"], "breakfast")
    assert Meal.objects.filter(user=user).count() == 1
    meal = Meal.objects.get(id=saved["meal_id"])
    assert meal.items.get().food.food_code == "IDLI"


@pytest.mark.django_db
def test_hindi_identifies_idli_and_breakfast(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="hi-idli@example.com")
    _auth(api_client, user)
    pending = _chat(api_client, "मैंने नाश्ते में दो इडली खाईं।")
    assert pending["confirmation"]["items"][0]["food_code"] == "IDLI"
    assert pending["confirmation"]["meal_type"] == "breakfast"
    assert pending["original_text"] == "मैंने नाश्ते में दो इडली खाईं।"
    assert Meal.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_tamil_and_telugu_idli_aliases(tmp_path):
    _load(tmp_path)
    tamil = resolve_food_mention("இட்லி", language="ta", semantic=False)
    telugu = resolve_food_mention("ఇడ్లీ", language="te", semantic=False)
    assert tamil["status"] == "resolved"
    assert tamil["food"].food_code == "IDLI"
    assert telugu["status"] == "resolved"
    assert telugu["food"].food_code == "IDLI"


@pytest.mark.django_db
def test_romanized_and_code_mixed_names(tmp_path):
    _load(tmp_path)
    assert resolve_food_mention("idly", semantic=False)["food"].food_code == "IDLI"
    mixed = extract_mentions("I ate ಇಡ್ಲಿ")
    assert mixed["items"][0]["food_query"]
    resolved = resolve_food_mention(mixed["items"][0]["food_query"], language="kn", semantic=False)
    assert resolved["food"].food_code == "IDLI"


@pytest.mark.django_db
def test_aliases_share_canonical_food_code(tmp_path):
    _load(tmp_path)
    names = ["idli", "ಇಡ್ಲಿ", "इडली", "idly"]
    codes = {resolve_food_mention(name, semantic=False)["food"].food_code for name in names}
    assert codes == {"IDLI"}


def test_quantity_extraction_is_independent_of_food_identity():
    assert parse_quantity_reply("350 grams") == {"quantity": "350", "unit": "g"}
    assert parse_quantity_reply("೩೫೦ ಗ್ರಾಂ") == {"quantity": "350", "unit": "g"}
    assert parse_quantity_reply("ಎರಡು") == {"quantity": "2", "unit": None}
    extracted = extract_mentions("ನಾನು ಎರಡು ಇಡ್ಲಿ ತಿಂದೆ.")
    assert extracted["items"][0]["quantity"] == "2"


@pytest.mark.django_db
def test_clarification_keeps_selected_food_id(api_client, make_user, tmp_path, monkeypatch):
    _load(tmp_path)
    user = make_user(email="upma-ml@example.com")
    _auth(api_client, user)
    opening = _chat(api_client, "I ate one plate of upma")
    monkeypatch.setattr(
        "apps.agent.workflow.resolve_food_mention",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("quantity must not search again")),
    )
    choice = _chat(api_client, "Rava upma", opening["conversation_id"])
    pending = _chat(api_client, "350 grams", opening["conversation_id"])
    assert pending["confirmation"]["items"][0]["food_code"] == "UPMA-S"
    assert pending["confirmation"]["items"][0]["unit"] == "g"
    draft = MealDraft.objects.get(conversation_id=opening["conversation_id"])
    assert draft.items[0]["food_code"] == "UPMA-S"
    assert Meal.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_unrelated_vectors_are_rejected(tmp_path):
    _load(tmp_path)
    version = Food.objects.get(food_code="MANGO").nutrition_rows.get().dataset_version
    vector = [0.0] * 384
    vector[0] = 1.0
    FoodEmbedding.objects.create(
        food=Food.objects.get(food_code="MANGO"),
        dataset_version=version,
        embedding=vector,
        text_representation="Mango",
        language="mul",
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    result = resolve_food("zzzz-not-food", embed=lambda texts: [vector])
    assert result["status"] == "not_found"


@pytest.mark.django_db
def test_missing_catalogue_food_is_explicit(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="missing-ml@example.com")
    _auth(api_client, user)
    reply = _chat(api_client, "I ate 100 g of dragonfruit")
    assert reply["meal_id"] is None
    assert "couldn't find" in reply["message"].casefold() or "could not" in reply["message"].casefold()
    assert Meal.objects.filter(user=user).count() == 0


def test_malformed_tool_arguments_are_rejected():
    empty = _extract_payload("openrouter", {"meal_type": "breakfast", "items": "idli"})
    assert empty["items"] == []
    skipped = _extract_payload(
        "openrouter",
        {"items": [{"food_query": {"name": "idli"}, "quantity": {"n": 2}, "unit": ["g"]}]},
    )
    assert skipped["items"] == []
    ok = _extract_payload("openrouter", {"items": [{"food_query": "idli", "quantity": 2, "unit": "piece"}]})
    assert ok["items"][0]["food_query"] == "idli"


@pytest.mark.django_db
def test_confirm_validation_error_names_the_field(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="valid-ml@example.com")
    _auth(api_client, user)
    pending = _chat(api_client, "I ate 2 pieces of idli")
    response = api_client.post("/api/agent/confirm/", {"conversation_id": pending["conversation_id"]}, format="json")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert "breakfast" in error["message"].casefold() or "meal" in error["message"].casefold()
    assert "meal_type" in error["details"]
    assert Meal.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_nutrition_stays_deterministic(tmp_path):
    _load(tmp_path)
    result = calculate_nutrition("IDLI", 2, "piece")
    assert result["food_code"] == "IDLI"
    assert result["nutrients"]["energy_kcal"] == Decimal("80")


@pytest.mark.django_db
def test_localized_confirmation_preserves_identity(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="confirm-ml@example.com")
    _auth(api_client, user)
    pending = _chat(api_client, "ನಾನು ಎರಡು ಇಡ್ಲಿ ತಿಂದೆ.")
    item = pending["confirmation"]["items"][0]
    assert item["food_code"] == "IDLI"
    assert item["food_name"] == "Idli"
    assert item.get("original_name")
    assert pending["original_text"] == "ನಾನು ಎರಡು ಇಡ್ಲಿ ತಿಂದೆ."


@pytest.mark.django_db
def test_one_meal_after_confirm_and_retry(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="once-ml@example.com")
    _auth(api_client, user)
    pending = _chat(api_client, "I ate 2 pieces of idli for breakfast")
    assert Meal.objects.filter(user=user).count() == 0
    first = _confirm(api_client, pending["conversation_id"], "breakfast")
    second = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": pending["conversation_id"], "meal_type": "breakfast"},
        format="json",
    )
    assert first["meal_id"]
    assert second.status_code == 404
    assert Meal.objects.filter(user=user).count() == 1


def test_rules_provider_still_extracts_english_idlis():
    result = RulesProvider().extract("I ate 2 idlis for breakfast")
    assert result["items"][0]["food_query"] == "idlis"
    assert result["meal_type"] == "breakfast"
