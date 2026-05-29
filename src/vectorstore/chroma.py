import logging
from pathlib import Path
from typing import Optional

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

from core.config import settings

logger = logging.getLogger(__name__)

# Singleton holders
_embeddings: Optional[GoogleGenerativeAIEmbeddings] = None
_vector_store: Optional[Chroma] = None

def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info("Initializing Google Generative AI Embeddings (gemini-embedding-001)")
        _embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
    return _embeddings

def get_vector_store(force_reload: bool = False) -> Chroma:
    global _vector_store
    if _vector_store is None or force_reload:
        db_path = settings.abs_chroma_db_path if settings else Path("data/embeddings/chroma_database")
        logger.info(f"Connecting to persistent Chroma vector database at: {db_path}")
        _vector_store = Chroma(
            persist_directory=str(db_path),
            embedding_function=get_embeddings()
        )
    return _vector_store

def persist_documents(documents, persist_directory: Path):
    """Persist a list of LangChain Document objects into a Chroma DB."""
    logger.info(f"Persisting {len(documents)} documents to Chroma at {persist_directory}")
    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=get_embeddings(),
        persist_directory=str(persist_directory)
    )
    # update singleton
    global _vector_store
    _vector_store = vector_db
    return vector_db
