from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, RemoveMessage
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    """
    State definition for the chatbot LangGraph.
    Tracks conversation history as an append-only list of LangChain messages.
    """
    messages: Annotated[List[BaseMessage], add_messages]


def delete_old_messages(state: ChatState) -> dict:
    """
    Cleanup node that deletes old messages from state to enforce a
    short-term memory (STM) size limit. If the message list grows beyond
    a modest threshold we remove the oldest messages using `RemoveMessage`.
    """
    msgs = state["messages"]

    # If there are more than 10 messages, remove the earliest 6
    if len(msgs) > 10:
        to_remove = msgs[:6]
        return {"messages": [RemoveMessage(id=m.id) for m in to_remove]}

    return {}
