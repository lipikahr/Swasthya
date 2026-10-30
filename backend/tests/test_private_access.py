import pytest
from rest_framework_simplejwt.tokens import RefreshToken

from apps.conversations.models import AgentAction, Conversation, Message
from apps.meals.models import Meal

pytestmark = pytest.mark.django_db

PRIVATE_GET = [
    "/api/agent/draft/?conversation_id=1",
    "/api/auth/me/",
    "/api/profile/",
    "/api/targets/",
    "/api/targets/history/",
    "/api/meals/",
    "/api/dashboard/",
    "/api/progress/daily/",
    "/api/progress/range/?start=2026-10-01&end=2026-10-07",
    "/api/streaks/",
    "/api/conversations/",
]

PRIVATE_POST = [
    "/api/agent/chat/",
    "/api/agent/confirm/",
    "/api/agent/draft/",
    "/api/agent/voice/",
    "/api/agent/transcribe/",
    "/api/targets/suggest/",
    "/api/targets/accept-suggestion/",
]


def _auth(api_client, user):
    access = str(RefreshToken.for_user(user).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return api_client


def test_unauthenticated_requests_cannot_read_or_change_private_data(api_client):
    for path in PRIVATE_GET:
        response = api_client.get(path)
        assert response.status_code == 401, path
    for path in PRIVATE_POST:
        response = api_client.post(path, {}, format="json")
        assert response.status_code == 401, path
    assert api_client.patch("/api/profile/", {"goal": "maintain"}, format="json").status_code == 401
    assert api_client.post("/api/meals/", {"items": []}, format="json").status_code == 401


def test_one_user_cannot_access_another_users_records(api_client, make_user):
    owner = make_user(email="owner-private@example.com")
    other = make_user(email="other-private@example.com")
    meal = Meal.objects.create(user=owner, meal_type="lunch")
    conversation = Conversation.objects.create(user=owner)
    Message.objects.create(conversation=conversation, role=Message.Role.USER, content="I ate idli")
    AgentAction.objects.create(
        conversation=conversation,
        action_type="extract",
        tool_name="rules",
        tool_input={"text": "I ate idli"},
        tool_output={"items": []},
        status="ok",
    )

    _auth(api_client, other)
    assert api_client.get(f"/api/meals/{meal.id}/").status_code == 404
    assert api_client.patch(f"/api/meals/{meal.id}/", {"meal_type": "dinner"}, format="json").status_code == 404
    assert api_client.delete(f"/api/meals/{meal.id}/").status_code == 404
    assert api_client.get(f"/api/conversations/{conversation.id}/").status_code == 404
    stolen_turn = api_client.post(
        "/api/agent/chat/",
        {"message": "2 idlis", "conversation_id": conversation.id},
        format="json",
    )
    assert stolen_turn.status_code == 404
    assert Meal.objects.filter(user=owner).count() == 1
    assert Conversation.objects.filter(user=other).count() == 0

    profile = api_client.get("/api/profile/").json()
    assert profile["goal"] == ""
    listed = api_client.get("/api/meals/").json()["results"]
    assert listed == []
    conversations = api_client.get("/api/conversations/").json()["results"]
    assert conversations == []


def test_meal_create_ignores_a_client_supplied_user_id(api_client, make_user):
    owner = make_user(email="meal-owner@example.com")
    other = make_user(email="meal-other@example.com")
    _auth(api_client, owner)
    response = api_client.post(
        "/api/meals/",
        {"user": other.id, "user_id": other.id, "items": [{"food_code": "missing", "quantity": "1", "unit": "g"}]},
        format="json",
    )
    assert response.status_code in {400, 404}
    assert Meal.objects.filter(user=other).count() == 0
