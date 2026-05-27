import os
import sys
import pytest
from pathlib import Path

# Insert src directory to path for imports to resolve cleanly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

@pytest.fixture(autouse=True)
def mock_env_keys(monkeypatch):
    """
    Automatically mocks required environment variables during tests
    to prevent configuration initialization failures.
    """
    monkeypatch.setenv("MISTRAL_API_KEY", "mock_mistral_key_for_testing_12345")
    monkeypatch.setenv("GOOGLE_API_KEY", "mock_google_key_for_testing_12345")
    monkeypatch.setenv("DATABASE_PATH", "data/test_chatbot.db")
    monkeypatch.setenv("CHROMA_DB_PATH", "data/test_chroma_database")
    monkeypatch.setenv("PDF_PATH", "data/test_melanoma.pdf")
