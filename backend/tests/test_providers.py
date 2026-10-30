import logging
import os
import threading
import time

import httpx
import pytest
from google.genai.errors import APIError, ClientError, ServerError

from apps.agent.providers import (
    EXTRACT_TIMEOUT_MS,
    GeminiProvider,
    OpenRouterProvider,
    ProviderError,
    RulesProvider,
    classify_gemini_exception,
    gemini_configuration,
    get_provider,
    probe_gemini,
)
from apps.agent.views import join_or_run_turn


def test_blank_process_value_does_not_hide_the_root_env(tmp_path, monkeypatch):
    from config.envfile import fill_blank_env_from_file

    path = tmp_path / ".env"
    path.write_text(
        "OPENROUTER_API_KEY=from-file\nOPENROUTER_BASE_URL=https://example.test/v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.setenv("DJANGO_SECRET_KEY", "keep-me")
    fill_blank_env_from_file(path)
    assert os.environ["OPENROUTER_API_KEY"] == "from-file"
    assert os.environ["OPENROUTER_BASE_URL"] == "https://example.test/v1"
    assert os.environ["DJANGO_SECRET_KEY"] == "keep-me"
    monkeypatch.setenv("OPENROUTER_API_KEY", "from-process")
    fill_blank_env_from_file(path)
    assert os.environ["OPENROUTER_API_KEY"] == "from-process"


def test_rules_provider_extracts_a_clear_sentence():
    result = RulesProvider().extract("I ate 2 idlis for breakfast")
    assert result["provider"] == "rules"
    assert result["meal_type"] == "breakfast"
    assert result["items"][0]["food_query"] == "idlis"
    assert result["items"][0]["quantity"] == "2"


def test_get_provider_uses_rules_when_no_key(settings):
    settings.OPENROUTER_API_KEY = ""
    settings.GEMINI_API_KEY = ""
    assert isinstance(get_provider(), RulesProvider)


def test_get_provider_prefers_openrouter_when_configured(settings, monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"meal_type": "breakfast", "items": [{"food_query": "idli", "quantity": 2, "unit": "idli"}]}'
                        }
                    }
                ]
            }

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["model"] = kwargs["json"]["model"]
        return FakeResponse()

    monkeypatch.setattr("httpx.post", fake_post)
    settings.OPENROUTER_API_KEY = "configured"
    settings.OPENROUTER_BASE_URL = "https://openrouter.example/api/v1/"
    settings.OPENROUTER_MODEL = "openai/gpt-4o-mini"
    settings.GEMINI_API_KEY = "also-set"
    provider = get_provider()
    assert isinstance(provider, OpenRouterProvider)
    assert provider.extract("I ate 2 idlis for breakfast")["provider"] == "openrouter"
    assert captured["url"] == "https://openrouter.example/api/v1/chat/completions"
    assert captured["model"] == "openai/gpt-4o-mini"


def test_get_provider_uses_gemini_when_key_is_configured(settings, monkeypatch):
    class FakeClient:
        def __init__(self, api_key, **kwargs):
            assert api_key
            options = kwargs.get("http_options")
            assert options is not None
            assert options.timeout == EXTRACT_TIMEOUT_MS
            assert options.retry_options is None
            self.models = self

        def generate_content(self, **kwargs):
            raise AssertionError("extract is not called in this test")

    monkeypatch.setattr("google.genai.Client", FakeClient)
    settings.GEMINI_API_KEY = "configured"
    settings.GEMINI_MODEL = "gemini-2.5-flash"
    provider = get_provider()
    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"
    assert provider.model == "gemini-2.5-flash"
    assert not hasattr(provider, "api_key")


def test_gemini_extract_parses_model_json(settings, monkeypatch):
    class FakeResponse:
        text = '{"meal_type": "lunch", "items": [{"food_query": "idli", "quantity": 2, "unit": "idli"}]}'

    class FakeClient:
        def __init__(self, api_key, **kwargs):
            self.models = self

        def generate_content(self, **kwargs):
            assert kwargs["model"] == "gemini-2.5-flash"
            return FakeResponse()

    monkeypatch.setattr("google.genai.Client", FakeClient)
    settings.GEMINI_API_KEY = "configured"
    settings.GEMINI_MODEL = "gemini-2.5-flash"
    provider = get_provider()
    result = provider.extract("I had 2 idli for lunch")
    assert result["provider"] == "gemini"
    assert result["meal_type"] == "lunch"
    assert result["items"][0]["food_query"] == "idli"
    assert result["intent"] in {"", "log_meal"}


def test_gemini_configuration_never_includes_the_key(settings):
    settings.GEMINI_API_KEY = "configured"
    settings.GEMINI_MODEL = "gemini-2.5-flash"
    status = gemini_configuration()
    assert status == {"key_configured": True, "provider": "gemini", "model": "gemini-2.5-flash"}
    assert "api_key" not in status
    assert "configured" not in status.values()


def test_probe_gemini_reports_empty_key_as_configuration(settings):
    settings.GEMINI_API_KEY = ""
    result = probe_gemini()
    assert result["ok"] is False
    assert result["key_configured"] is False
    assert result["provider"] == "rules"
    assert result["live_request"] == "not_attempted"
    assert result["error_class"] == "configuration"


def test_classify_gemini_credentials_model_rate_limit_and_network():
    credentials = ClientError(403, {"error": {"status": "PERMISSION_DENIED", "message": "denied", "code": 403}})
    model = ClientError(404, {"error": {"status": "NOT_FOUND", "message": "model missing", "code": 404}})
    rate = ClientError(429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": "quota", "code": 429}})
    invalid_key = APIError(400, {"error": {"status": "INVALID_ARGUMENT", "message": "API key not valid", "code": 400}})
    server = ServerError(503, {"error": {"status": "UNAVAILABLE", "message": "model overloaded", "code": 503}})
    deadline = ServerError(504, {"error": {"status": "DEADLINE_EXCEEDED", "message": "deadline", "code": 504}})
    assert classify_gemini_exception(credentials)[0] == "credentials"
    assert classify_gemini_exception(model)[0] == "model"
    assert classify_gemini_exception(rate)[0] == "rate_limit"
    assert classify_gemini_exception(invalid_key)[0] == "credentials"
    assert classify_gemini_exception(server) == (
        "unavailable",
        "The language model is temporarily unavailable. Try again shortly.",
    )
    assert classify_gemini_exception(deadline)[0] == "timeout"
    assert classify_gemini_exception(httpx.ConnectError("offline"))[0] == "network"
    assert classify_gemini_exception(httpx.ReadTimeout("slow"))[0] == "timeout"


def test_gemini_extract_maps_provider_errors(settings, monkeypatch):
    class FakeClient:
        def __init__(self, api_key, **kwargs):
            self.models = self

        def generate_content(self, **kwargs):
            raise ClientError(429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": "quota", "code": 429}})

    monkeypatch.setattr("google.genai.Client", FakeClient)
    settings.GEMINI_API_KEY = "configured"
    try:
        get_provider().extract("I ate 1 idli")
    except ProviderError as exc:
        assert exc.reason == "rate_limit"
        assert "quota" not in str(exc).lower()
        assert exc.__cause__ is not None
    else:
        raise AssertionError("expected ProviderError")


def test_gemini_extract_retries_unavailable_then_succeeds(settings, monkeypatch):
    calls = {"n": 0}

    class FakeResponse:
        text = '{"meal_type": "breakfast", "items": [{"food_query": "idli", "quantity": 2, "unit": "idli"}]}'

    class FakeClient:
        def __init__(self, api_key, **kwargs):
            self.models = self

        def generate_content(self, **kwargs):
            calls["n"] += 1
            if calls["n"] < 3:
                raise ServerError(503, {"error": {"status": "UNAVAILABLE", "message": "overloaded", "code": 503}})
            return FakeResponse()

    monkeypatch.setattr("google.genai.Client", FakeClient)
    monkeypatch.setattr("apps.agent.providers.time.sleep", lambda _delay: None)
    settings.GEMINI_API_KEY = "configured"
    result = get_provider().extract("I ate 2 idlis today")
    assert calls["n"] == 3
    assert result["provider"] == "gemini"
    assert result["items"][0]["food_query"] == "idli"


def test_openrouter_log_includes_status_and_hides_secrets(settings, monkeypatch, caplog):
    request = httpx.Request("POST", "https://openrouter.example/api/v1/chat/completions")
    response = httpx.Response(
        401,
        json={"error": {"message": "invalid key sk-or-v1-secretvalue", "code": 401}},
        request=request,
    )

    def fake_post(*args, **kwargs):
        raise httpx.HTTPStatusError("boom", request=request, response=response)

    monkeypatch.setattr("httpx.post", fake_post)
    settings.OPENROUTER_API_KEY = "configured"
    settings.OPENROUTER_BASE_URL = "https://openrouter.example/api/v1"
    caplog.set_level(logging.WARNING)
    with pytest.raises(ProviderError) as caught:
        get_provider().extract("I ate 2 idlis for breakfast")
    assert caught.value.reason == "credentials"
    assert "sk-or-v1-secretvalue" not in str(caught.value)
    assert "sk-or-v1-secretvalue" not in caplog.text
    assert "I ate 2 idlis" not in caplog.text
    assert "http_code=401" in caplog.text
    assert "[redacted]" in caplog.text


def test_chat_endpoint_selects_openrouter_and_logs_the_meal(api_client, make_user, settings, monkeypatch, tmp_path):
    from decimal import Decimal

    from apps.conversations.models import Message
    from apps.meals.models import Meal
    from tests.test_application import _auth, _load_foods

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"meal_type": "breakfast", "items": [{"food_query": "idli", "quantity": 2, "unit": "idli"}]}'
                        }
                    }
                ]
            }

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["model"] = kwargs["json"]["model"]
        captured["has_authorization"] = kwargs["headers"]["Authorization"].startswith("Bearer ")
        return FakeResponse()

    monkeypatch.setattr("httpx.post", fake_post)
    settings.OPENROUTER_API_KEY = "configured"
    settings.OPENROUTER_BASE_URL = "https://openrouter.example/api/v1"
    settings.OPENROUTER_MODEL = "openai/gpt-4o-mini"
    settings.GEMINI_API_KEY = "also-set"
    _load_foods(tmp_path)
    user = make_user(email="openrouter-chat@example.com")
    _auth(api_client, user)
    logged = api_client.post("/api/agent/chat/", {"message": "I ate 2 idlis for breakfast"}, format="json")
    assert logged.status_code == 200
    body = logged.json()
    assert body["status"] == "AWAITING_CONFIRMATION"
    assert body["provider"] == "openrouter"
    assert body["meal_id"] is None
    assert body["confirmation"]["meal_type"] == "breakfast"
    assert Decimal(body["confirmation"]["items"][0]["nutrition"]["energy_kcal"]) == Decimal("80")
    assert captured["url"] == "https://openrouter.example/api/v1/chat/completions"
    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["has_authorization"] is True
    assert not Meal.objects.filter(user=user).exists()
    confirmed = api_client.post(
        "/api/agent/confirm/",
        {"conversation_id": body["conversation_id"], "meal_type": "breakfast"},
        format="json",
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "SUCCESS"
    meal = Meal.objects.get(user=user)
    assert meal.items.get().food.food_code == "IDLI"
    assert Message.objects.filter(conversation_id=body["conversation_id"], role="user").count() == 1
    assert Message.objects.filter(conversation_id=body["conversation_id"], role="assistant").count() == 2


def test_join_or_run_turn_reuses_an_in_flight_result():
    started = threading.Event()
    release = threading.Event()
    calls = {"n": 0}

    def run():
        calls["n"] += 1
        started.set()
        release.wait(timeout=2)
        return {"status": "SUCCESS", "message": "Logged 2 idli Idli."}

    results = [None, None]

    def owner():
        results[0] = join_or_run_turn(4242, "I ate 2 idlis today", run)

    def waiter():
        started.wait(timeout=2)
        results[1] = join_or_run_turn(4242, "I ate 2 idlis today", run)

    first = threading.Thread(target=owner)
    second = threading.Thread(target=waiter)
    first.start()
    second.start()
    assert started.wait(timeout=2)
    time.sleep(0.05)
    release.set()
    first.join(timeout=2)
    second.join(timeout=2)
    assert calls["n"] == 1
    assert results[0] == results[1]
    assert results[0]["status"] == "SUCCESS"
