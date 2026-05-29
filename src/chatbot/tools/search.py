import logging
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Initialize default search run
_ddg_search = DuckDuckGoSearchRun(region="us-en")


@tool
def duckduckgo_search(query: str) -> str:
    """
    Perform a live web search using DuckDuckGo to find real-time, current, or factual information on the internet.
    Use this tool when the user asks about recent events, news, weather, or topics where live, external data is required.
    NOTE: In production environments, web searches may require explicit human reviewer approval before executing.

    Args:
        query: The search query string to look up on the web.

    Returns:
        A string summarizing search results, snippets, or headlines from matching web pages.
    """
    logger.info(f"DuckDuckGo search tool invoked with query: '{query}'")
    try:
        return _ddg_search.invoke(query)
    except Exception as e:
        logger.error(f"Error executing web search: {e}", exc_info=True)
        return f"Error executing web search: {str(e)}"
