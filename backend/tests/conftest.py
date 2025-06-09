import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the backend directory to sys.path to allow 'from main import app'
# This assumes conftest.py is in backend/tests/
# and main.py is in backend/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app  # Import the FastAPI app instance

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
