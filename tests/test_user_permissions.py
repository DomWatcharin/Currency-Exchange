import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

@pytest.fixture
def admin_headers():
    return {"X-API-Key": settings.admin_api_key}

@pytest.fixture
def user_headers():
    return {"X-API-Key": settings.user_api_key}

def test_admin_access(admin_headers):
    response = client.get("/users", headers=admin_headers)
    assert response.status_code == 200

def test_user_access_denied(user_headers):
    response = client.get("/users", headers=user_headers)
    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}

def test_user_access_allowed(user_headers):
    response = client.get("/exchange-rates", headers=user_headers)
    assert response.status_code == 200

def test_admin_access_allowed(admin_headers):
    response = client.get("/exchange-rates", headers=admin_headers)
    assert response.status_code == 200
