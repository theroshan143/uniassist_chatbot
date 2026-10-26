"""Pytest configuration and common fixtures."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment flags
os.environ["DEMO_MODE"] = "true"
os.environ["ADMIN_PASSWORD"] = "test_admin_pass"
os.environ["SQLITE_DB_PATH"] = ":memory:"

from app.database import Base, engine, SessionLocal
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create in-memory tables for tests."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client
