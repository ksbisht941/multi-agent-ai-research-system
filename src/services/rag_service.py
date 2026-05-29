import logging
from pathlib import Path

from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import settings
from vectorstore.chroma import get_vector_store, persist_documents

logger = logging.getLogger(__name__)


def index_document() -> dict:
    pdf_path = (
        settings.abs_pdf_path if settings else Path("data/raw/yolo_melanoma_final.pdf")
    )
    logger.info(f"Starting document indexing. Loading PDF: {pdf_path}")

    if not pdf_path.exists():
        error_msg = f"MELANOMA PDF FILE NOT FOUND AT: {pdf_path.resolve()}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}

    try:
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        logger.info(f"Loaded PDF document containing {len(docs)} pages.")

        splitter = RecursiveCharacterTextSplitter(chunk_size=150, chunk_overlap=200)
        chunks = splitter.split_documents(docs)
        logger.info(f"Split PDF into {len(chunks)} chunks.")

        db_path = (
            settings.abs_chroma_db_path
            if settings
            else Path("data/embeddings/chroma_database")
        )
        persist_documents(chunks, db_path)

        logger.info("RAG Indexing successfully completed!")
        return {
            "status": "success",
            "message": f"Successfully indexed {len(docs)} pages into {len(chunks)} vector segments.",
            "chunks_count": len(chunks),
        }
    except Exception as e:
        logger.error(f"Error during RAG indexing: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@tool
def rag_tool(query: str) -> dict:
    """Retrieve relevant passages from the indexed PDF using semantic similarity."""
    logger.info(f"RAG tool invoked with query: '{query}'")
    try:
        vector_db = get_vector_store()

        db_path = (
            settings.abs_chroma_db_path
            if settings
            else Path("data/embeddings/chroma_database")
        )
        db_files = list(db_path.glob("**/*")) if db_path.exists() else []

        if not db_files or len(db_files) < 2:
            logger.warning(
                "RAG vector database appears to be empty! Attempting auto-indexing first..."
            )
            index_res = index_document()
            if index_res["status"] == "error":
                return {
                    "query": query,
                    "context": [],
                    "metadata": [],
                    "warning": "RAG database is empty and auto-indexing failed. Please trigger indexing manual step.",
                }

        retriever = vector_db.as_retriever(
            search_type="similarity", search_kwargs={"k": 4}
        )
        result = retriever.invoke(query)

        context = [doc.page_content for doc in result]
        metadata = [doc.metadata for doc in result]

        logger.info(f"Retrieved {len(context)} matching passages.")
        return {"query": query, "context": context, "metadata": metadata}
    except Exception as e:
        logger.error(f"Error in RAG tool: {e}", exc_info=True)
        return {
            "query": query,
            "context": [],
            "metadata": [],
            "error": f"Failed to retrieve context: {str(e)}",
        }
