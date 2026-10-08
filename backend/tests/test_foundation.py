import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_urls(settings):
    settings.ROOT_URLCONF = "tests.urls_for_tests"


def test_health_endpoint_is_public_and_reports_database(api_client):
    response = api_client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True}


def test_custom_user_uses_email_login_and_lowercases():
    User = get_user_model()
    user = User.objects.create_user(email="Lipika@Example.COM", password="x" * 12, name="L")
    assert user.email == "lipika@example.com"
    assert User.USERNAME_FIELD == "email"
    assert user.check_password("x" * 12)


def test_create_user_requires_email():
    with pytest.raises(ValueError):
        get_user_model().objects.create_user(email="", password="x", name="n")


def test_openapi_schema_and_docs_are_public(api_client):
    assert api_client.get("/api/schema/").status_code == 200
    assert api_client.get("/api/docs/").status_code == 200


def test_endpoints_require_a_token_by_default(api_client, test_urls):
    response = api_client.get("/protected/")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_valid_jwt_access_token_authenticates(api_client, make_user, test_urls):
    user = make_user()
    access = str(RefreshToken.for_user(user).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api_client.get("/protected/")
    assert response.status_code == 200
    assert response.json() == {"email": user.email}


def test_garbage_token_is_rejected(api_client, test_urls):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert api_client.get("/protected/").status_code == 401


def test_validation_errors_use_structured_shape(api_client, make_user, test_urls):
    user = make_user()
    api_client.force_authenticate(user)
    response = api_client.post("/validated/", {"age": 0}, format="json")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert "age" in error["details"]
