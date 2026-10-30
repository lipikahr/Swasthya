from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.conversations.models import MealDraft
from apps.meals.models import Meal
from tests.test_application import _auth
from tests.test_meal_draft import _chat, _confirm, _load
from tests.test_nutrition import _row, _write


@pytest.mark.django_db
def test_explicit_breakfast_is_preselected_and_unspecified_requires_a_choice(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="category@example.com")
    _auth(api_client, user)

    named = _chat(api_client, "I ate 2 pieces of idli for breakfast")
    assert named["status"] == "AWAITING_CONFIRMATION"
    assert named["confirmation"]["meal_type"] == "breakfast"
    assert named["confirmation"]["meal_type_required"] is False
    assert Meal.objects.filter(user=user).count() == 0

    plain = _chat(api_client, "I ate 2 pieces of idli")
    assert plain["status"] == "AWAITING_CONFIRMATION"
    assert plain["confirmation"]["meal_type"] is None
    assert plain["confirmation"]["meal_type_required"] is True
    missing = api_client.post("/api/agent/confirm/", {"conversation_id": plain["conversation_id"]}, format="json")
    assert missing.status_code == 400
    snack = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": plain["conversation_id"], "meal_type": "brunch", "user_id": 999},
        format="json",
    )
    assert snack.status_code == 400
    assert Meal.objects.filter(user=user).count() == 0

    edited = api_client.post(
        "/api/agent/draft/",
        {"conversation_id": plain["conversation_id"], "action": "edit", "meal_type": "dinner"},
        format="json",
    )
    assert edited.status_code == 200
    assert edited.json()["confirmation"]["meal_type"] == "dinner"
    assert Meal.objects.filter(user=user).count() == 0
    draft = MealDraft.objects.get(conversation_id=plain["conversation_id"], user=user)
    assert draft.meal_type == "dinner"

    saved = _confirm(api_client, plain["conversation_id"], "lunch")
    meal = Meal.objects.get(id=saved["meal_id"], user=user)
    assert meal.meal_type == "lunch"
    listed = api_client.get("/api/meals/").json()["results"]
    assert listed[0]["id"] == meal.id
    assert listed[0]["meal_type"] == "lunch"


@pytest.mark.django_db
def test_editing_and_cancelling_a_pending_meal_do_not_save_it(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="edit-cancel@example.com")
    _auth(api_client, user)
    pending = _chat(api_client, "I ate 2 pieces of idli for breakfast")
    assert Decimal(pending["confirmation"]["items"][0]["nutrition"]["energy_kcal"]) == Decimal("80")

    edited = api_client.post(
        "/api/agent/draft/",
        {
            "conversation_id": pending["conversation_id"],
            "action": "edit",
            "items": [{"food_query": "Idli", "quantity": "1", "unit": "piece"}],
        },
        format="json",
    )
    assert edited.status_code == 200
    body = edited.json()
    assert body["status"] == "AWAITING_CONFIRMATION"
    assert body["meal_id"] is None
    assert Decimal(body["confirmation"]["items"][0]["quantity"]) == Decimal("1")
    assert Decimal(body["confirmation"]["items"][0]["nutrition"]["energy_kcal"]) == Decimal("40")
    assert Meal.objects.filter(user=user).count() == 0

    cancelled = api_client.post(
        "/api/agent/draft/",
        {"conversation_id": pending["conversation_id"], "action": "cancel"},
        format="json",
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["meal_id"] is None
    assert "won't log" in cancelled.json()["message"]
    assert not MealDraft.objects.filter(user=user).exists()
    assert Meal.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_pending_confirmation_does_not_change_dashboard_totals(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="dashboard-pending@example.com")
    _auth(api_client, user)
    before = api_client.get("/api/dashboard/").json()["progress"]["consumed"]["energy_kcal"]
    pending = _chat(api_client, "I ate 2 pieces of idli for breakfast")
    assert pending["status"] == "AWAITING_CONFIRMATION"
    during = api_client.get("/api/dashboard/").json()["progress"]["consumed"]["energy_kcal"]
    assert Decimal(during) == Decimal(before)
    _confirm(api_client, pending["conversation_id"], "breakfast")
    after = api_client.get("/api/dashboard/").json()["progress"]["consumed"]["energy_kcal"]
    assert Decimal(after) == Decimal(before) + Decimal("80")


@pytest.mark.django_db
def test_confirmation_keeps_missing_nutrients_blank(api_client, make_user, tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(path, [_row(food_code="ROTI", food_name="Millet roti", energy_kcal=100, fibre_g=None)])
    from apps.nutrition.ingestion import load_nutrition

    load_nutrition(path)
    user = make_user(email="blank-nutrient@example.com")
    _auth(api_client, user)
    pending = _chat(api_client, "I ate 100 grams of millet roti for lunch")
    nutrition = pending["confirmation"]["items"][0]["nutrition"]
    assert nutrition["fibre_g"] is None
    assert Decimal(nutrition["energy_kcal"]) == Decimal("100")
    saved = _confirm(api_client, pending["conversation_id"], "lunch")
    snapshot = Meal.objects.get(id=saved["meal_id"]).items.get().nutrition_snapshot
    assert snapshot["fibre_g"] is None
    assert snapshot["fibre_g"] != "0"


@pytest.mark.django_db
def test_expired_draft_and_other_users_cannot_confirm(api_client, make_user, tmp_path):
    _load(tmp_path)
    owner = make_user(email="owner-confirm@example.com")
    other = make_user(email="other-confirm@example.com")
    _auth(api_client, owner)
    pending = _chat(api_client, "I ate 2 pieces of idli for breakfast")
    draft = MealDraft.objects.get(conversation_id=pending["conversation_id"])
    MealDraft.objects.filter(pk=draft.pk).update(updated_at=timezone.now() - timedelta(hours=25))

    expired = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": pending["conversation_id"], "meal_type": "breakfast", "user_id": other.id},
        format="json",
    )
    assert expired.status_code == 400
    assert Meal.objects.filter(user=owner).count() == 0
    assert not MealDraft.objects.filter(user=owner).exists()

    _auth(api_client, owner)
    fresh = _chat(api_client, "I ate 2 pieces of idli for breakfast")
    _auth(api_client, other)
    stolen = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": fresh["conversation_id"], "meal_type": "dinner"},
        format="json",
    )
    assert stolen.status_code == 404
    assert Meal.objects.count() == 0
