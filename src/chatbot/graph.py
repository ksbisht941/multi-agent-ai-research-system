import os
import sqlite3
import logging
from typing import Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from langchain_mistralai import ChatMistralAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command

from chatbot.config import settings
from chatbot.state import ChatState
from chatbot.tools import tools

logger = logging.getLogger(__name__)

# CacheCompiledGraph singleton
_compiled_chatbot = None

def route_tools(state: ChatState) -> Literal["human_approval", "tools", "__end__"]:
    """
    Decides routing after the agent chat node:
      - No tool calls detected                    → END (reply directly)
      - First tool call is 'duckduckgo_search'   → Route to human approval gate
      - Any other tool call                       → Route directly to execution tools
    """
    last_message = state["messages"][-1]
    if not getattr(last_message, "tool_calls", None):
        return END
        
    tool_name = last_message.tool_calls[0]["name"]
    if tool_name == "duckduckgo_search":
        logger.info("Web search tool call detected. Routing to human_approval node.")
        return "human_approval"
        
    logger.info(f"Tool call '{tool_name}' detected. Routing directly to tools node.")
    return "tools"

def chat_node(state: ChatState) -> dict:
    """
    Chat node that evaluates the message history, trims older messages to respect
    the short-term memory budget, and invokes the Mistral LLM with tool capabilities.
    """
    max_tokens = settings.MAX_TOKEN_BUDGET if settings else 1000
    model_name = settings.MISTRAL_MODEL if settings else "mistral-large-latest"
    
    # Trim the conversation history using approximate tokens counts
    trimmed_history = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=max_tokens
    )
    
    logger.info(f"Trimmed history to {count_tokens_approximately(trimmed_history)} tokens (budget: {max_tokens})")
    
    # Initialize LLM with Mistral API Key and bind tools
    llm = ChatMistralAI(model=model_name)
    llm_with_tools = llm.bind_tools(tools)
    
    # Invoke model with trimmed history to stay under token budgets
    response = llm_with_tools.invoke(trimmed_history)
    return {"messages": [response]}

def human_approval_node(state: ChatState) -> Command:
    """
    Human-in-the-loop interrupt gate. Pauses the state machine and requests
    user review for duckduckgo_search queries.
    
    Returns:
        A Command that routes to 'tools' (if approved) or END (if rejected).
    """
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    query = tool_call["args"].get("query", str(tool_call["args"]))
    
    logger.info("LangGraph interrupt triggered: Awaiting Human approval for Search query.")
    
    # Pause graph execution and output interrupt info
    decision = interrupt({
        "type": "approval",
        "tool_name": tool_call["name"],
        "query": query,
        "instruction": "Web search requires human approval. Approve? (yes/no)"
    })
    
    # Check decision returned from resume command
    if decision.get("approved", "").strip().lower() == "no":
        logger.info("Human reviewer rejected the web search query.")
        
        # Mistral requires a ToolMessage response for every tool_call in history to prevent 400 errors.
        # We append a cancellation ToolMessage followed by a human-friendly AI cancellation message.
        return Command(
            goto=END,
            update={
                "messages": [
                    ToolMessage(
                        content="Cancelled: rejected by human reviewer.",
                        tool_call_id=tool_call["id"]
                    ),
                    AIMessage(content="❌ Web search was rejected by the human reviewer.")
                ]
            }
        )
        
    logger.info("Human reviewer approved the web search. Resuming execution...")
    return Command(goto="tools")

def get_chatbot(force_recompile: bool = False):
    """
    Compiles and returns the compiled LangGraph StateGraph.
    Uses SqliteSaver checkpointer pointing to settings.abs_database_path.
    """
    global _compiled_chatbot
    if _compiled_chatbot is None or force_recompile:
        logger.info("Assembling LangGraph workflow...")
        
        # Initialize graph
        workflow = StateGraph(ChatState)
        
        # Define nodes
        workflow.add_node("chat_node", chat_node)
        workflow.add_node("tools", ToolNode(tools))
        workflow.add_node("human_approval", human_approval_node)
        
        # Define transitions and conditional logic
        workflow.add_edge(START, "chat_node")
        workflow.add_conditional_edges(
            "chat_node",
            route_tools,
            ["human_approval", "tools", END]
        )
        workflow.add_edge("tools", "chat_node")
        
        # Setup persistent SQLite Checkpointer
        db_path = settings.abs_database_path if settings else "data/chatbot.db"
        
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        logger.info(f"Connecting SqliteSaver checkpointer to database: {db_path}")
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        
        # Compile graph
        _compiled_chatbot = workflow.compile(checkpointer=checkpointer)
        logger.info("LangGraph workflow compiled successfully.")
        
    return _compiled_chatbot
