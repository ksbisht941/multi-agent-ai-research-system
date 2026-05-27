from langchain_core.messages import AIMessage
from chatbot.graph import route_tools

def test_route_tools_no_calls():
    """
    Verifies that a message without tool calls routes directly to the END.
    """
    state = {
        "messages": [AIMessage(content="Hello! How can I assist you today?")]
    }
    
    res = route_tools(state)
    assert res == "__end__"

def test_route_tools_search_approval():
    """
    Verifies that a DuckDuckGo search tool call routes to the human approval gate.
    """
    msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "duckduckgo_search",
            "args": {"query": "AI research papers"},
            "id": "call_search_123"
        }]
    )
    state = {"messages": [msg]}
    
    res = route_tools(state)
    assert res == "human_approval"

def test_route_tools_other_execution():
    """
    Verifies that standard tools route directly to immediate tool execution.
    """
    msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "calculator",
            "args": {"first_num": 10, "second_num": 2, "operation": "div"},
            "id": "call_calc_123"
        }]
    )
    state = {"messages": [msg]}
    
    res = route_tools(state)
    assert res == "tools"
