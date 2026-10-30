import re

import pytest
from django.core import mail
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

GENERIC = "If an account exists for that email address, a reset link has been sent."


def _extract_reset(body: str):
    match = re.search(r"uid=([^&\s]+)&token=([^\s]+)", body)
    assert match, body
    return match.group(1), match.group(2)


def test_reset_request_is_generic_when_the_email_is_unknown(api_client):
    response = api_client.post("/api/auth/password-reset/", {"email": "missing@example.com"}, format="json")
    assert response.status_code == 200
    assert response.json()["message"] == GENERIC
    assert mail.outbox == []


def test_reset_request_does_not_say_whether_the_account_exists(api_client, make_user):
    make_user(email="asha@example.com")
    known = api_client.post("/api/auth/password-reset/", {"email": "asha@example.com"}, format="json")
    unknown = api_client.post("/api/auth/password-reset/", {"email": "other@example.com"}, format="json")
    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(mail.outbox) == 1
    assert "asha@example.com" not in known.json()["message"]


def test_reset_confirm_changes_the_password_once(api_client, make_user):
    user = make_user(email="reset@example.com", password="Old-pass-12345")
    requested = api_client.post("/api/auth/password-reset/", {"email": "reset@example.com"}, format="json")
    assert requested.status_code == 200
    uid, token = _extract_reset(mail.outbox[0].body)

    valid = api_client.post("/api/auth/password-reset/validate/", {"uid": uid, "token": token}, format="json")
    assert valid.status_code == 200
    assert valid.json()["valid"] is True

    confirmed = api_client.post(
        "/api/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "password": "New-pass-12345"},
        format="json",
    )
    assert confirmed.status_code == 200
    user.refresh_from_db()
    assert user.check_password("New-pass-12345")

    login = api_client.post(
        "/api/auth/login/",
        {"email": "reset@example.com", "password": "New-pass-12345"},
        format="json",
    )
    assert login.status_code == 200

    reused = api_client.post(
        "/api/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "password": "Third-pass-12345"},
        format="json",
    )
    assert reused.status_code == 400
    user.refresh_from_db()
    assert user.check_password("New-pass-12345")


def test_reset_request_stays_generic_when_email_delivery_fails(api_client, make_user, monkeypatch):
    make_user(email="mailfail@example.com")

    def boom(*args, **kwargs):
        raise RuntimeError("smtp down")

    monkeypatch.setattr("apps.accounts.password_reset.send_mail", boom)
    known = api_client.post("/api/auth/password-reset/", {"email": "mailfail@example.com"}, format="json")
    unknown = api_client.post("/api/auth/password-reset/", {"email": "other@example.com"}, format="json")
    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json() == {"message": GENERIC}


def test_reset_confirm_rejects_a_bad_token(api_client, make_user):
    user = make_user(email="token@example.com")
    uid = RefreshToken.for_user(user)
    response = api_client.post(
        "/api/auth/password-reset/confirm/",
        {"uid": "not-a-uid", "token": str(uid), "password": "Another-pass-123"},
        format="json",
    )
    assert response.status_code == 400
    assert User.objects.get(email="token@example.com").check_password("StrongPass#12345")
