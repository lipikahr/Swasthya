from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile

import pytest
from django.utils import timezone
from openpyxl import Workbook
from rest_framework_simplejwt.tokens import RefreshToken

from apps.agent.languages import SUPPORTED_LANGUAGES, detect_language
from apps.conversations.models import Conversation, Message
from apps.meals.models import Meal
from apps.nutrition.allergens import allergen_conflict
from apps.nutrition.ingestion import load_nutrition
from apps.nutrition.nutrients import NUTRIENT_FIELDS
from apps.progress.goal import record_new_achievement, status_from_progress
from apps.progress.models import DailyGoalAchievement
from apps.progress.services import get_daily_progress

pytestmark = pytest.mark.django_db


def _auth(api_client, user):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")
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
        _food(food_code="IDLI", food_name="Idli", energy_kcal=100, protein_g=4, servings_unit="idli", unit_serving_energy_kcal=40),
        _food(food_code="RICE1", food_name="Brown rice", energy_kcal=130, protein_g=3),
        _food(food_code="CHKN", food_name="Chicken curry", energy_kcal=180, protein_g=18),
        _food(food_code="MILK1", food_name="Milk", energy_kcal=60, protein_g=3),
        _food(food_code="PANE", food_name="Paneer bhurji", energy_kcal=220, protein_g=14),
    ]
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    path = tmp_path / "foods.xlsx"
    workbook.save(path)
    load_nutrition(path)


def _set_target(api_client, calories="200"):
    api_client.post(
        "/api/targets/customize/",
        {"calories": calories, "protein_g": "80", "carbohydrates_g": "200", "fat_g": "60", "fibre_g": "25"},
        format="json",
    )


def test_goal_statuses_and_saved_meals_only(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    user = make_user(email="goals@example.com")
    _auth(api_client, user)
    _set_target(api_client, "200")
    empty = api_client.get("/api/progress/daily/").json()
    assert empty["goal_status"] == "no_data"
    assert empty["goal_label"] == "No data"
    conversation = Conversation.objects.create(user=user)
    pending = api_client.post(
        "/api/agent/chat/",
        {"message": "I ate 100 g brown rice", "conversation_id": conversation.id},
        format="json",
    )
    assert pending.json()["status"] == "AWAITING_CONFIRMATION"
    still_empty = api_client.get("/api/progress/daily/").json()
    assert still_empty["goal_status"] == "no_data"
    api_client.post(
        "/api/meals/",
        {"items": [{"food_code": "RICE1", "quantity": "100", "unit": "g"}]},
        format="json",
    )
    below = api_client.get("/api/progress/daily/").json()
    assert below["goal_status"] == "below"
    api_client.post(
        "/api/meals/",
        {"items": [{"food_code": "RICE1", "quantity": "50", "unit": "g"}]},
        format="json",
    )
    met = api_client.get("/api/progress/daily/").json()
    assert met["goal_status"] == "met"
    api_client.post(
        "/api/meals/",
        {"items": [{"food_code": "CHKN", "quantity": "100", "unit": "g"}]},
        format="json",
    )
    above = api_client.get("/api/progress/daily/").json()
    assert above["goal_status"] == "above"
    assert status_from_progress(get_daily_progress(user), Decimal("200")) == "above"


def test_weekly_monthly_range_and_timezone_day(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    user = make_user(email="range@example.com")
    _auth(api_client, user)
    _set_target(api_client, "130")
    meal = api_client.post(
        "/api/meals/",
        {
            "timestamp": "2026-10-08T22:30:00Z",
            "items": [{"food_code": "RICE1", "quantity": "100", "unit": "g"}],
        },
        format="json",
    )
    assert meal.status_code == 201
    day = api_client.get("/api/progress/daily/?date=2026-10-08").json()
    assert day["goal_status"] == "met"
    assert Decimal(day["consumed"]["energy_kcal"]) == Decimal("130")
    neighbour = api_client.get("/api/progress/daily/?date=2026-10-09").json()
    assert neighbour["goal_status"] == "no_data"
    week = api_client.get("/api/progress/range/?start=2026-10-05&end=2026-10-11").json()
    assert week["summary"]["met"] == 1
    assert week["summary"]["no_data"] == 6
    month = api_client.get("/api/progress/range/?start=2026-10-01&end=2026-10-31").json()
    assert month["summary"]["met"] == 1
    assert len(month["days"]) == 31


def test_celebration_only_on_new_met_after_save(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    user = make_user(email="celebrate@example.com")
    _auth(api_client, user)
    _set_target(api_client, "130")
    conversation = Conversation.objects.create(user=user)
    first = api_client.post("/api/agent/chat/", {"message": "I ate 100 g brown rice", "conversation_id": conversation.id}, format="json")
    assert first.json()["status"] == "AWAITING_CONFIRMATION"
    failed = api_client.post("/api/agent/confirm/", {"conversation_id": conversation.id, "meal_type": "brunch"}, format="json")
    assert failed.status_code == 400
    assert DailyGoalAchievement.objects.count() == 0
    saved = api_client.post("/api/agent/confirm/", {"conversation_id": conversation.id, "meal_type": "lunch"}, format="json")
    assert saved.status_code == 200
    assert saved.json()["celebration"]["show"] is True
    again = record_new_achievement(user=user, day=timezone.now().date(), before="met", after="met", meal=Meal.objects.get())
    assert again is None
    extra = api_client.post("/api/agent/chat/", {"message": "I ate 100 g idli", "conversation_id": conversation.id}, format="json")
    if extra.json().get("status") == "AWAITING_CONFIRMATION":
        second = api_client.post("/api/agent/confirm/", {"conversation_id": conversation.id, "meal_type": "dinner"}, format="json")
        assert second.json().get("celebration") in (None, {})
    meal = Meal.objects.filter(user=user).first()
    api_client.delete(f"/api/meals/{meal.id}/")
    assert DailyGoalAchievement.objects.filter(user=user).count() == 0


def test_allergies_and_suggestions_are_filtered(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    user = make_user(email="allergy@example.com")
    _auth(api_client, user)
    blank = api_client.get("/api/profile/").json()
    assert blank["allergies_status"] == ""
    saved = api_client.patch(
        "/api/profile/",
        {
            "allergies_status": "listed",
            "allergies": ["milk", "peanut"],
            "dislikes": ["idli"],
            "diet_pattern": "vegetarian",
            "preferred_cuisines": ["south indian"],
            "preferred_language": "en",
        },
        format="json",
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["allergies"] == ["milk", "peanut"]
    assert allergen_conflict("Paneer bhurji", body["allergies"]) == "milk"
    assert allergen_conflict("Chicken curry", ["milk"]) is None
    _set_target(api_client, "2000")
    conversation = Conversation.objects.create(user=user)
    reply = api_client.post(
        "/api/agent/chat/",
        {"message": "Suggest something for lunch", "conversation_id": conversation.id},
        format="json",
    )
    payload = reply.json()
    assert payload["status"] == "SUGGESTIONS"
    names = [item["food_name"].casefold() for item in payload["suggestions"]]
    assert all("paneer" not in name and "milk" not in name and "chicken" not in name and "idli" not in name for name in names)
    assert payload["allergy_note"]
    assert Meal.objects.filter(user=user).count() == 0
    none = api_client.patch("/api/profile/", {"allergies_status": "none", "allergies": ["milk"]}, format="json")
    assert none.json()["allergies"] == []
    assert none.json()["allergies_status"] == "none"


def test_native_script_messages_and_supported_languages(api_client, make_user):
    user = make_user(email="lang@example.com")
    _auth(api_client, user)
    assert {code for code, _name in SUPPORTED_LANGUAGES} >= {
        "as",
        "bn",
        "brx",
        "doi",
        "gu",
        "hi",
        "kn",
        "ks",
        "kok",
        "mai",
        "ml",
        "mni",
        "mr",
        "ne",
        "or",
        "pa",
        "sa",
        "sat",
        "sd",
        "ta",
        "te",
        "ur",
        "en",
    }
    samples = {
        "kn": "ನಾನು ಇಡ್ಲಿ ತಿಂದೆ",
        "hi": "मैंने इडली खाई",
        "ta": "நான் இட்லி சாப்பிட்டேன்",
        "te": "నేను ఇడ్లీ తిన్నాను",
        "bn": "আমি ইডলি খেয়েছি",
    }
    conversation = Conversation.objects.create(user=user)
    for code, text in samples.items():
        assert detect_language(text, "en") == code
        reply = api_client.post("/api/agent/chat/", {"message": text, "conversation_id": conversation.id}, format="json")
        assert reply.status_code == 200
        stored = Message.objects.filter(conversation=conversation, role=Message.Role.USER, content=text).exists()
        assert stored
        assert reply.json()["original_text"] == text
    failed = detect_language("hello", "ta")
    assert failed == "ta"


def test_transcription_endpoint_and_errors(api_client, make_user, settings):
    user = make_user(email="voice@example.com")
    _auth(api_client, user)
    missing = api_client.post("/api/agent/transcribe/", {}, format="multipart")
    assert missing.status_code in {400, 503}
    settings.SARVAM_API_KEY = "test-key"
    upload = SimpleUploadedFile("speech.webm", b"not-real-audio", content_type="audio/webm")
    with patch("apps.agent.speech.httpx.post") as mocked:
        mocked.return_value.status_code = 200
        mocked.return_value.json.return_value = {"transcript": "ನಾನು ಚಪಾತಿ ತಿಂದೆ", "language_code": "kn"}
        response = api_client.post("/api/agent/transcribe/", {"audio": upload}, format="multipart")
    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "ನಾನು ಚಪಾತಿ ತಿಂದೆ"
    assert body["submitted"] is False
    assert "test-key" not in str(response.content)
    blank = api_client.post(
        "/api/agent/transcribe/",
        {"audio": SimpleUploadedFile("speech.webm", b"", content_type="audio/webm")},
        format="multipart",
    )
    assert blank.status_code == 400
    with patch("apps.agent.speech.httpx.post") as mocked:
        mocked.return_value.status_code = 429
        mocked.return_value.json.return_value = {}
        limited = api_client.post(
            "/api/agent/transcribe/",
            {"audio": SimpleUploadedFile("speech.webm", b"abc", content_type="audio/webm")},
            format="multipart",
        )
    assert limited.status_code == 502
    with patch("apps.agent.speech.httpx.post") as mocked:
        mocked.return_value.status_code = 401
        mocked.return_value.json.return_value = {"error": {"message": "unauthorized"}}
        denied_key = api_client.post(
            "/api/agent/transcribe/",
            {"audio": SimpleUploadedFile("speech.webm", b"abc", content_type="audio/webm")},
            format="multipart",
        )
    assert denied_key.status_code == 403
    assert denied_key.json()["error"]["code"] == "invalid_credentials"
    api_client.credentials()
    denied = api_client.post("/api/agent/transcribe/", {}, format="multipart")
    assert denied.status_code == 401
