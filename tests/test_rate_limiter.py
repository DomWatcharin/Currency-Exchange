import pytest
import time
import os
from fastapi.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.main import app
from app.core.config import settings

client = TestClient(app)

@pytest.fixture
def admin_headers():
    return {"X-API-Key": settings.admin_api_key}

@pytest.fixture
def user_headers():
    return {"X-API-Key": settings.user_api_key}

@pytest.fixture
def user_headers_list():
    user_api_keys = os.getenv("USER_API_KEYS", "").split(",")
    return [{"X-API-Key": api_key} for api_key in user_api_keys if api_key]

def test_rate_limit_exceeded(user_headers):
    for _ in range(100):
        response = client.get("/exchange-rates", headers=user_headers)
        assert response.status_code == 200

    response = client.get("/exchange-rates", headers=user_headers)
    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}

def test_rate_limit_not_exceeded(user_headers):
    for _ in range(99):
        response = client.get("/exchange-rates", headers=user_headers)
        assert response.status_code == 200

    # Add a delay to ensure the rate limiter window resets
    time.sleep(1)

    response = client.get("/exchange-rates", headers=user_headers)
    assert response.status_code == 200

def test_rate_limit_on_get_users(admin_headers):
    for _ in range(100):
        response = client.get("/users", headers=admin_headers)
        assert response.status_code == 200

    response = client.get("/users", headers=admin_headers)
    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}

def test_multiple_users_rate_limit(user_headers_list):
    headers_list = user_headers_list + [{"X-API-Key": settings.admin_api_key}]

    def make_requests(headers):
        for _ in range(100):
            response = client.get("/exchange-rates", headers=headers)
            assert response.status_code == 200

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_requests, headers) for headers in headers_list]
        for future in as_completed(futures):
            future.result()

    # Ensure that each user can make 100 requests without exceeding the rate limit
    for headers in headers_list:
        response = client.get("/exchange-rates", headers=headers)
        assert response.status_code == 429
        assert response.json() == {"detail": "Rate limit exceeded"}
