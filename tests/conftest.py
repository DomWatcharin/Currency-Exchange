import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the root directory to the PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db import Base, get_db
from app.middleware.rate_limiter import RateLimiterMiddleware

# Create a test database engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./tests/test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the test database
Base.metadata.create_all(bind=engine)

# Override the get_db dependency to use the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def test_client():
    client = TestClient(app)
    yield client

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    # Setup: Create the test database
    Base.metadata.create_all(bind=engine)
    yield
    # Teardown: Drop the test database
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    for middleware in app.user_middleware:
        if isinstance(middleware.cls, RateLimiterMiddleware):
            middleware.cls.reset()
            break

@pytest.fixture(scope="module", autouse=True)
def set_user_api_keys():
    os.environ["USER_API_KEYS"] = "user_api_key_1,user_api_key_2,user_api_key_3,user_api_key_4,user_api_key_5,user_api_key_6,user_api_key_7,user_api_key_8,user_api_key_9,user_api_key_10,user_api_key_11,user_api_key_12,user_api_key_13,user_api_key_14,user_api_key_15,user_api_key_16,user_api_key_17,user_api_key_18,user_api_key_19,user_api_key_20"

