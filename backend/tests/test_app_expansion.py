import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.meals.models import Meal
from apps.nutrition.allergens import restriction_conflict, suggestion_allowed
from apps.nutrition.models import UserFood
from apps.profiles.models import UserProfile
from tests.test_application import _auth
from tests.test_meal_draft import _chat, _load


@pytest.mark.django_db
def test_profile_appearance_and_restrictions(api_client, make_user):
    user = make_user(email="settings@example.com")
    _auth(api_client, user)
    empty = api_client.get("/api/profile/")
    assert empty.status_code == 200
    assert empty.json()["appearance"] == "light"
    assert empty.json()["autoplay_replies"] is False
    saved = api_client.patch(
        "/api/profile/",
        {"appearance": "dark", "restrictions": ["no onion"], "likes": ["idli"], "notes": "mild", "autoplay_replies": True},
        format="json",
    )
    assert saved.status_code == 200
    assert saved.json()["appearance"] == "dark"
    assert "no onion" in saved.json()["restrictions"]
    system = api_client.patch("/api/profile/", {"appearance": "system"}, format="json")
    assert system.json()["appearance"] == "system"


def test_stt_language_hint_uses_bcp47_and_skips_english():
    from apps.agent.speech import _stt_language_hint

    assert _stt_language_hint("kn") == "kn-IN"
    assert _stt_language_hint("ta-IN") == "ta-IN"
    assert _stt_language_hint("en") is None
    assert _stt_language_hint("") is None


@pytest.mark.django_db
def test_weekly_targets_optional(api_client, make_user):
    user = make_user(email="weekly@example.com")
    _auth(api_client, user)
    UserProfile.objects.create(
        user=user,
        date_of_birth="1990-01-01",
        sex="female",
        height_cm="160",
        weight_kg="60",
        activity_level="sedentary",
        goal="maintain",
    )
    daily = api_client.post(
        "/api/targets/customize/",
        {"calories": "1800", "protein_g": "70", "carbohydrates_g": "200", "fat_g": "60", "fibre_g": "25"},
        format="json",
    )
    assert daily.status_code == 201
    assert daily.json()["weekly_calories"] is None
    weekly = api_client.post(
        "/api/targets/customize/",
        {
            "calories": "1800",
            "protein_g": "70",
            "carbohydrates_g": "200",
            "fat_g": "60",
            "fibre_g": "25",
            "weekly_calories": "12000",
        },
        format="json",
    )
    assert weekly.status_code == 201
    assert weekly.json()["weekly_calories"] == "12000.00"
    dash = api_client.get("/api/dashboard/")
    assert dash.json()["weekly"]["derived_from_daily"] is False


@pytest.mark.django_db
def test_user_food_isolation_and_logging(api_client, make_user, tmp_path):
    _load(tmp_path)
    owner = make_user(email="foods@example.com")
    other = make_user(email="other-foods@example.com")
    _auth(api_client, owner)
    created = api_client.post(
        "/api/user-foods/",
        {
            "name": "Asha mix",
            "ingredients": "rice, dal",
            "serving_amount": "100",
            "serving_unit": "g",
            "energy_kcal": "150",
            "protein_g": "6",
        },
        format="json",
    )
    assert created.status_code == 201
    food_id = created.json()["id"]
    assert created.json()["provenance"] == "user_provided"
    assert UserFood.objects.get(pk=food_id).user_id == owner.id
    meal = api_client.post(
        "/api/meals/",
        {"meal_type": "snack", "items": [{"user_food_id": food_id, "quantity": "100", "unit": "g"}]},
        format="json",
    )
    assert meal.status_code == 201
    assert meal.json()["items"][0]["provenance"] == "user_provided"
    _auth(api_client, other)
    stolen = api_client.get(f"/api/user-foods/{food_id}/")
    assert stolen.status_code == 404


@pytest.mark.django_db
def test_restriction_filter_excludes_onion():
    assert restriction_conflict("onion uttapam", ["no onion"]) == "no onion"
    allowed, reason = suggestion_allowed(name="Asha mix", ingredients="", profile=None, require_ingredients=True)
    assert allowed is False
    assert reason == "unverified"


@pytest.mark.django_db
def test_snack_confirm_and_plan_does_not_count(api_client, make_user, tmp_path):
    _load(tmp_path)
    user = make_user(email="plan@example.com")
    _auth(api_client, user)
    api_client.post(
        "/api/targets/customize/",
        {"calories": "2000", "protein_g": "80", "carbohydrates_g": "250", "fat_g": "70", "fibre_g": "30"},
        format="json",
    )
    named = _chat(api_client, "I ate 100 g brown rice for snack")
    assert named["status"] == "AWAITING_CONFIRMATION"
    saved = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": named["conversation_id"], "meal_type": "snack"},
        format="json",
    )
    assert saved.status_code == 200
    assert Meal.objects.filter(user=user, meal_type="snack").count() == 1
    generated = api_client.post("/api/day-plans/", {"date": saved.json().get("date") or None}, format="json")
    assert generated.status_code in {200, 201, 400}
    meals_before = Meal.objects.filter(user=user).count()
    generated2 = api_client.post("/api/day-plans/", {}, format="json")
    assert generated2.status_code in {200, 201}
    assert Meal.objects.filter(user=user).count() == meals_before
    if generated2.json().get("slots"):
        slot_id = generated2.json()["slots"][0]["id"]
        draft = api_client.post(f"/api/day-plans/slots/{slot_id}/log/", {}, format="json")
        assert draft.status_code == 200
        assert draft.json()["confirmation"]
        assert Meal.objects.filter(user=user).count() == meals_before


@pytest.mark.django_db
def test_plan_manual_extra_and_south_filter(api_client, make_user, tmp_path):
    from apps.nutrition.food_profile import classify_name
    from apps.profiles.models import UserProfile

    _load(tmp_path)
    user = make_user(email="plan-pref@example.com")
    _auth(api_client, user)
    UserProfile.objects.create(
        user=user,
        date_of_birth="1990-01-01",
        sex="female",
        height_cm="160",
        weight_kg="60",
        activity_level="sedentary",
        goal="lose",
        diet_pattern="vegetarian",
        preferred_cuisines=["South Indian"],
        likes=["idli"],
    )
    api_client.post(
        "/api/targets/customize/",
        {"calories": "1800", "protein_g": "70", "carbohydrates_g": "200", "fat_g": "60", "fibre_g": "25"},
        format="json",
    )
    added = api_client.post(
        "/api/day-plans/slots/",
        {"date": "2026-05-01", "slot": "breakfast", "food_code": "IDLI", "quantity": "2", "unit": "piece", "label": "Early"},
        format="json",
    )
    assert added.status_code == 201
    extra = api_client.post(
        "/api/day-plans/slots/",
        {"date": "2026-05-01", "slot": "breakfast", "food_code": "IDLI", "quantity": "1", "unit": "piece", "label": "Second breakfast"},
        format="json",
    )
    assert extra.status_code == 201, extra.json()
    breakfast = [row for row in extra.json()["slots"] if row["slot"] == "breakfast"]
    assert len(breakfast) == 2
    generated = api_client.post("/api/day-plans/", {"date": "2026-05-01"}, format="json")
    assert generated.status_code == 201
    regions = {classify_name(row["food_name"])["region"] for row in generated.json()["slots"]}
    assert "north" not in regions
    sweets = {classify_name("Gulab jamun")["is_sweet"]}
    assert True in sweets
    removed = api_client.delete(f"/api/day-plans/slots/{breakfast[0]['id']}/")
    assert removed.status_code == 200


@pytest.mark.django_db
def test_image_and_speak_unconfigured(api_client, make_user, settings):
    settings.OPENROUTER_API_KEY = ""
    settings.SARVAM_API_KEY = ""
    user = make_user(email="media@example.com")
    _auth(api_client, user)
    image = SimpleUploadedFile("food.jpg", b"not-an-image", content_type="image/jpeg")
    photo = api_client.post("/api/agent/image/", {"image": image})
    assert photo.status_code == 503
    speak = api_client.post("/api/agent/speak/", {"text": "Hello"}, format="json")
    assert speak.status_code == 503
    bad = api_client.post("/api/agent/image/", {"image": SimpleUploadedFile("food.gif", b"gif", content_type="image/gif")})
    assert bad.status_code == 400
