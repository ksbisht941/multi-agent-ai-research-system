import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base workspace directory path
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Centralized configuration settings for the AI Assistant.
    Loads configurations from environment variables or a .env file.
    """
    # ── API Keys ─────────────────────────────────────────────────────────────
    # Required for ChatMistralAI agent
    MISTRAL_API_KEY: str
    
    # Required for GoogleGenerativeAIEmbeddings
    GOOGLE_API_KEY: str

    # ── Server Config ────────────────────────────────────────────────────────
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ── Database & Storage Paths ─────────────────────────────────────────────
    # Paths are relative to the project root directory.
    DATABASE_PATH: str = "data/db/chatbot.db"
    CHROMA_DB_PATH: str = "data/embeddings/chroma_database"
    PDF_PATH: str = "data/raw/yolo_melanoma_final.pdf"
    OUTPUT_PATH: str = "data/output"
    
    # ── LLM Token Configurations ──────────────────────────────────────────────
    MAX_TOKEN_BUDGET: int = 150
    MISTRAL_MODEL: str = "mistral-large-latest"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def abs_database_path(self) -> Path:
        """Returns the absolute path to the SQLite database."""
        path = Path(self.DATABASE_PATH)
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def abs_chroma_db_path(self) -> Path:
        """Returns the absolute path to the Chroma Vector Database."""
        path = Path(self.CHROMA_DB_PATH)
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def abs_pdf_path(self) -> Path:
        """Returns the absolute path to the RAG PDF document."""
        path = Path(self.PDF_PATH)
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def abs_output_path(self) -> Path:
        """Returns the absolute path to the generated output directory."""
        path = Path(self.OUTPUT_PATH)
        return path if path.is_absolute() else BASE_DIR / path

# Instantiate the settings manager
try:
    settings = Settings()
except Exception as e:
    # If .env is missing or invalid in dev/production environments, we can print a friendly hint
    # but still allow import so CLI / Server can present standard validation messages.
    settings = None
    import sys
    print(
        f"\n[WARNING] Configuration Error: {e}\n"
        "Please ensure a '.env' file exists in your project root with MISTRAL_API_KEY and GOOGLE_API_KEY defined.\n"
        "Refer to '.env.example' for reference.\n",
        file=sys.stderr
    )
