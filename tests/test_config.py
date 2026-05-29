from pathlib import Path
from chatbot.config import Settings


def test_settings_load(monkeypatch):
    """
    Verifies that Settings correctly loads overridden environment variables.
    """
    monkeypatch.setenv("MISTRAL_API_KEY", "test_mistral")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google")
    monkeypatch.setenv("MAX_TOKEN_BUDGET", "500")

    settings = Settings()

    assert settings.MISTRAL_API_KEY == "test_mistral"
    assert settings.GOOGLE_API_KEY == "test_google"
    assert settings.MAX_TOKEN_BUDGET == 500


def test_absolute_paths_resolve():
    """
    Verifies that settings resolve database and document paths relative to project root.
    """
    settings = Settings()

    assert isinstance(settings.abs_database_path, Path)
    assert settings.abs_database_path.name == "test_chatbot.db"

    assert isinstance(settings.abs_chroma_db_path, Path)
    assert settings.abs_chroma_db_path.name == "test_chroma_database"
