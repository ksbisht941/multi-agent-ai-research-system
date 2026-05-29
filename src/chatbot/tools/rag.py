"""Compatibility shim: re-export RAG functions from `services.rag_service`.

This file keeps the old import path `chatbot.tools.rag` working while the
implementation lives under `src/services/rag_service.py`.
"""

from services.rag_service import index_document, rag_tool

__all__ = ["index_document", "rag_tool"]
