import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(email="user@example.com", password="StrongPass#12345", name="Test User"):
        return User.objects.create_user(email=email, password=password, name=name)

    return _make
