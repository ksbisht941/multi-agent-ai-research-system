import logging
import sqlite3
from pathlib import Path

from core.config import settings, BASE_DIR

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = BASE_DIR / Path("data/db/chatbot.db")


def get_database_path() -> Path:
    """Return the configured SQLite database path, falling back to the default path."""
    return settings.abs_database_path if settings else DEFAULT_DB_PATH


def ensure_db_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_sqlite_connection(timeout: int = 30, check_same_thread: bool = False) -> sqlite3.Connection:
    db_path = get_database_path()
    ensure_db_parent(db_path)
    logger.info(f"Opening SQLite connection to {db_path}")
    return sqlite3.connect(str(db_path), timeout=timeout, check_same_thread=check_same_thread)
