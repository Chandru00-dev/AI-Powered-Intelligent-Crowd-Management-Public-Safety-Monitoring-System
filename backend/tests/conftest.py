import pytest
from backend.app.core.init_app import initialize_system

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure database tables and initial demo seeds are prepared before running tests."""
    initialize_system()
