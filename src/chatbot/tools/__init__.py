"""Tools used by the chatbot (scheduler, rag, math, etc.)."""

from .math import calculator
from .search import duckduckgo_search
from .scheduler import generate_day_plan, generate_schedule_pdf
from services.rag_service import rag_tool

# Aggregated list of all tools exposed to the LangGraph AI agent
tools = [
    duckduckgo_search,
    calculator,
    rag_tool,
    generate_day_plan,
    generate_schedule_pdf,
]

__all__ = [
    "calculator",
    "duckduckgo_search",
    "generate_day_plan",
    "generate_schedule_pdf",
    "rag_tool",
    "tools",
]
