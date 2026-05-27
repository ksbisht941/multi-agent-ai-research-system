from chatbot.tools.math import calculator
from chatbot.tools.search import duckduckgo_search
from chatbot.tools.scheduler import generate_day_plan, generate_schedule_pdf
from chatbot.tools.rag import rag_tool

# Aggregated list of all tools exposed to the LangGraph AI agent
tools = [
    duckduckgo_search,
    calculator,
    rag_tool,
    generate_day_plan,
    generate_schedule_pdf
]

__all__ = [
    "calculator",
    "duckduckgo_search",
    "generate_day_plan",
    "generate_schedule_pdf",
    "rag_tool",
    "tools"
]
