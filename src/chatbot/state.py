from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    """
    State definition for the chatbot LangGraph.
    Tracks conversation history as an append-only list of LangChain messages.
    """
    messages: Annotated[List[BaseMessage], add_messages]
