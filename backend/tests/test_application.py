from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from django.utils import timezone
from openpyxl import Workbook
from rest_framework_simplejwt.tokens import RefreshToken

from apps.meals.models import Meal
from apps.nutrition.ingestion import load_nutrition
from apps.nutrition.nutrients import NUTRIENT_FIELDS
from apps.progress.services import get_streaks
from apps.targets.engine import suggest_targets
from apps.targets.models import NutritionTarget

pytestmark = pytest.mark.django_db


def _auth(api_client, user):
    access = str(RefreshToken.for_user(user).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return api_client


def _headers():
    return (
        ["food_code", "food_name", "primarysource", "servings_unit"]
        + list(NUTRIENT_FIELDS)
        + [f"unit_serving_{name}" for name in NUTRIENT_FIELDS]
    )


def _food(**overrides):
    row = {name: 0 for name in NUTRIENT_FIELDS}
    row.update({f"unit_serving_{name}": None for name in NUTRIENT_FIELDS})
    row.update({"primarysource": "test", "servings_unit": ""})
    row.update(overrides)
    return row


def _load_foods(tmp_path: Path):
    workbook = Workbook()
    sheet = workbook.active
    headers = _headers()
    sheet.append(headers)
    rows = [
        _food(food_code="IDLI", food_name="Idli", energy_kcal=100, servings_unit="idli", unit_serving_energy_kcal=40),
        _food(food_code="RICE1", food_name="Brown rice", energy_kcal=130),
        _food(food_code="RICE2", food_name="White rice", energy_kcal=130),
    ]
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    path = tmp_path / "foods.xlsx"
    workbook.save(path)
    load_nutrition(path)


def test_target_formula_matches_the_documented_defaults():
    result = suggest_targets(
        sex="male",
        age_years=26,
        height_cm=Decimal("180"),
        weight_kg=Decimal("80"),
        activity_level="sedentary",
        goal="maintain",
    )
    assert result["calories"] == Decimal("2160")
    assert result["protein_g"] == Decimal("64.00")
    assert result["fat_g"] == Decimal("72.00")
    assert result["carbohydrates_g"] == Decimal("314.00")
    assert result["fibre_g"] == Decimal("30.24")


def test_register_login_me_and_logout(api_client):
    created = api_client.post(
        "/api/auth/register/",
        {"email": "Person@Example.com", "name": "Person", "password": "Long-pass-123"},
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["user"]["email"] == "person@example.com"
    refresh = created.json()["refresh"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {created.json()['access']}")
    assert api_client.get("/api/auth/me/").json()["name"] == "Person"

    api_client.credentials()
    logged_in = api_client.post(
        "/api/auth/login/",
        {"email": "person@example.com", "password": "Long-pass-123"},
        format="json",
    )
    assert logged_in.status_code == 200
    assert "access" in logged_in.json()

    denied = api_client.post("/api/auth/logout/", {"refresh": refresh}, format="json")
    assert denied.status_code == 200
    reused = api_client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
    assert reused.status_code == 401


def test_profile_and_custom_targets_are_not_replaced_by_a_suggestion(api_client, make_user):
    user = make_user(email="target@example.com")
    _auth(api_client, user)
    saved = api_client.patch(
        "/api/profile/",
        {
            "date_of_birth": "2000-01-01",
            "sex": "male",
            "height_cm": "180",
            "weight_kg": "80",
            "activity_level": "sedentary",
            "goal": "maintain",
        },
        format="json",
    )
    assert saved.status_code == 200

    custom = api_client.post(
        "/api/targets/customize/",
        {"calories": "1800", "protein_g": "100", "carbohydrates_g": "150", "fat_g": "60", "fibre_g": "30"},
        format="json",
    )
    assert custom.status_code == 201
    suggestion = api_client.post("/api/targets/suggest/")
    assert suggestion.status_code == 200
    assert suggestion.json()["saved"] is False
    assert suggestion.json()["current_source"] == "user_customized"
    current = api_client.get("/api/targets/").json()["target"]
    assert current["source"] == "user_customized"
    assert Decimal(current["calories"]) == Decimal("1800")

    accepted = api_client.post("/api/targets/accept-suggestion/")
    assert accepted.status_code == 201
    assert accepted.json()["source"] == "system_suggested"
    assert Decimal(accepted.json()["calories"]) == Decimal("2160")
    history = api_client.get("/api/targets/history/").json()["results"]
    assert len(history) == 2
    assert NutritionTarget.objects.filter(user=user, source="user_customized", effective_until__isnull=False).exists()


def test_meal_log_uses_verified_nutrition_and_hides_other_users(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    owner = make_user(email="owner@example.com")
    other = make_user(email="other@example.com")
    _auth(api_client, owner)
    created = api_client.post(
        "/api/meals/",
        {"meal_type": "breakfast", "items": [{"food_code": "IDLI", "quantity": "2", "unit": "idli"}]},
        format="json",
    )
    assert created.status_code == 201
    body = created.json()
    assert body["items"][0]["dataset_version"] == "anuvaad-indb-2024.11"
    assert Decimal(body["items"][0]["nutrition_snapshot"]["energy_kcal"]) == Decimal("80")

    rejected = api_client.post(
        "/api/meals/",
        {"items": [{"food_code": "IDLI", "quantity": "1", "unit": "bowl"}]},
        format="json",
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "unsupported_unit"
    assert Meal.objects.filter(user=owner).count() == 1

    _auth(api_client, other)
    assert api_client.get(f"/api/meals/{body['id']}/").status_code == 404


def test_progress_sums_snapshots_and_streaks_follow_logged_days(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    user = make_user(email="progress@example.com")
    _auth(api_client, user)
    api_client.post(
        "/api/targets/customize/",
        {"calories": "2000", "protein_g": "80", "carbohydrates_g": "200", "fat_g": "60", "fibre_g": "25"},
        format="json",
    )
    api_client.post(
        "/api/meals/",
        {"items": [{"food_code": "RICE1", "quantity": "100", "unit": "g"}]},
        format="json",
    )
    progress = api_client.get("/api/progress/daily/").json()
    assert Decimal(progress["consumed"]["energy_kcal"]) == Decimal("130")
    assert Decimal(progress["remaining"]["calories"]) == Decimal("1870")
    dashboard = api_client.get("/api/dashboard/").json()
    assert dashboard["target"]["source"] == "user_customized"
    assert dashboard["streaks"]["weekly"] == 1

    earlier = timezone.make_aware(datetime(2026, 10, 1, 12, 0))
    meal = Meal.objects.filter(user=user).get()
    meal.timestamp = earlier
    meal.save(update_fields=["timestamp"])
    streaks = get_streaks(user, date(2026, 10, 8))
    assert streaks["weekly"] == 1
    Meal.objects.create(user=user, timestamp=timezone.make_aware(datetime(2026, 10, 8, 12, 0)), meal_type="lunch")
    # A meal with no items does not count. Add the rice item by logging through the API on that day.
    logged = api_client.post(
        "/api/meals/",
        {
            "timestamp": "2026-10-08T12:00:00Z",
            "items": [{"food_code": "RICE1", "quantity": "100", "unit": "g"}],
        },
        format="json",
    )
    assert logged.status_code == 201
    assert get_streaks(user, date(2026, 10, 8))["weekly"] == 2


def test_text_agent_logs_only_after_a_single_food_is_resolved(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    user = make_user(email="agent@example.com")
    _auth(api_client, user)
    logged = api_client.post("/api/agent/chat/", {"message": "I ate 2 idlis for breakfast"}, format="json")
    assert logged.status_code == 200
    assert logged.json()["status"] == "AWAITING_CONFIRMATION"
    assert Meal.objects.filter(user=user).count() == 0
    confirmed = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": logged.json()["conversation_id"], "meal_type": "breakfast"},
        format="json",
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "SUCCESS"
    meal = Meal.objects.get(user=user)
    assert meal.meal_type == "breakfast"
    assert meal.items.get().food.food_code == "IDLI"
    assert Decimal(meal.items.get().nutrition_snapshot["energy_kcal"]) == Decimal("80")

    unclear = api_client.post("/api/agent/chat/", {"message": "I had 250 grams of rice"}, format="json")
    assert unclear.json()["status"] == "NEEDS_CLARIFICATION"
    assert Meal.objects.filter(user=user).count() == 1

    missing = api_client.post("/api/agent/chat/", {"message": "I ate idli"}, format="json")
    assert missing.json()["status"] == "NEEDS_CLARIFICATION"
    assert "How much" in missing.json()["message"]

    other = make_user(email="intruder@example.com")
    _auth(api_client, other)
    stolen = api_client.get(f"/api/conversations/{logged.json()['conversation_id']}/")
    assert stolen.status_code == 404
    assert api_client.post("/api/agent/voice/", {}, format="json").status_code == 400
    spoken = api_client.post(
        "/api/agent/voice/",
        {"transcript": "I ate 2 idlis for breakfast"},
        format="json",
    )
    assert spoken.status_code == 200
    assert spoken.json()["status"] == "AWAITING_CONFIRMATION"
    assert Meal.objects.filter(user=other).count() == 0
    spoken_confirm = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": spoken.json()["conversation_id"], "meal_type": "breakfast"},
        format="json",
    )
    assert spoken_confirm.status_code == 200
    assert spoken_confirm.json()["status"] == "SUCCESS"
    assert Meal.objects.filter(user=other).count() == 1
