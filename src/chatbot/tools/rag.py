import os
import logging
from typing import Optional
from pathlib import Path
from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

from chatbot.config import settings

logger = logging.getLogger(__name__)

# Global instances (Singletons) to cache database connections
_embeddings: Optional[GoogleGenerativeAIEmbeddings] = None
_vector_store: Optional[Chroma] = None

def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Returns the Google Gemini Embeddings singleton instance."""
    global _embeddings
    if _embeddings is None:
        logger.info("Initializing Google Generative AI Embeddings (gemini-embedding-001)")
        # GoogleGenerativeAIEmbeddings automatically reads GOOGLE_API_KEY from environment
        _embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
    return _embeddings

def get_vector_store(force_reload: bool = False) -> Chroma:
    """
    Returns the persistent Chroma vector store singleton.
    Loads from settings.abs_chroma_db_path.
    """
    global _vector_store
    if _vector_store is None or force_reload:
        db_path = settings.abs_chroma_db_path if settings else Path("data/chroma_database")
        logger.info(f"Connecting to persistent Chroma vector database at: {db_path}")
        
        # Instantiate Chroma
        _vector_store = Chroma(
            persist_directory=str(db_path),
            embedding_function=get_embeddings()
        )
    return _vector_store

def index_document() -> dict:
    """
    Loads the PDF research paper, splits it into chunks, and indexes it into the vector store.
    This should be run once during setup or triggered via CLI/API.
    """
    pdf_path = settings.abs_pdf_path if settings else Path("data/yolo_melanoma_final.pdf")
    logger.info(f"Starting document indexing. Loading PDF: {pdf_path}")
    
    if not pdf_path.exists():
        error_msg = f"MELANOMA PDF FILE NOT FOUND AT: {pdf_path.resolve()}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}
        
    try:
        # Load PDF
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        logger.info(f"Loaded PDF document containing {len(docs)} pages.")
        
        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=150, chunk_overlap=200)
        chunks = splitter.split_documents(docs)
        logger.info(f"Split PDF into {len(chunks)} chunks.")
        
        # Overwrite/Create database and persist
        db_path = settings.abs_chroma_db_path if settings else Path("data/chroma_database")
        logger.info(f"Persisting {len(chunks)} text chunks to Chroma at {db_path}...")
        
        vector_db = Chroma.from_documents(
            documents=chunks,
            embedding=get_embeddings(),
            persist_directory=str(db_path)
        )
        
        # Update our active singleton
        global _vector_store
        _vector_store = vector_db
        
        logger.info("RAG Indexing successfully completed!")
        return {
            "status": "success",
            "message": f"Successfully indexed {len(docs)} pages into {len(chunks)} vector segments.",
            "chunks_count": len(chunks)
        }
    except Exception as e:
        logger.error(f"Error during RAG indexing: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@tool
def rag_tool(query: str) -> dict:
    """
    Retrieve highly relevant passages and reference material from the Melanoma Study Research Paper PDF.
    Use this tool when users ask factual, technical, medical, or conceptual questions related to YOLO,
    melanoma classification, convolutional neural networks in dermatology, or study results.
    
    Args:
        query: The semantic search query or question to retrieve matching literature content.
        
    Returns:
        A dictionary containing the query, matching passages ('context'), and matching 'metadata' references.
    """
    logger.info(f"RAG tool invoked with query: '{query}'")
    try:
        vector_db = get_vector_store()
        
        # Verify if database actually has documents (checking if files exist in directory)
        db_path = settings.abs_chroma_db_path if settings else Path("data/chroma_database")
        # Chroma writes sqlite/parquet/etc files in its folder
        db_files = list(db_path.glob("**/*")) if db_path.exists() else []
        
        if not db_files or len(db_files) < 2:
            logger.warning("RAG vector database appears to be empty! Attempting auto-indexing first...")
            index_res = index_document()
            if index_res["status"] == "error":
                return {
                    "query": query,
                    "context": [],
                    "metadata": [],
                    "warning": "RAG database is empty and auto-indexing failed. Please trigger indexing manual step."
                }
        
        # Run retrieval (top 4 matching chunks)
        retriever = vector_db.as_retriever(search_type='similarity', search_kwargs={'k': 4})
        result = retriever.invoke(query)
        
        context = [doc.page_content for doc in result]
        metadata = [doc.metadata for doc in result]
        
        logger.info(f"Retrieved {len(context)} matching passages.")
        return {
            'query': query,
            'context': context,
            'metadata': metadata
        }
    except Exception as e:
        logger.error(f"Error in RAG tool: {e}", exc_info=True)
        return {
            "query": query,
            "context": [],
            "metadata": [],
            "error": f"Failed to retrieve context: {str(e)}"
        }
