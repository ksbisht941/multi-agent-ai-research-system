import os
import uuid
import logging
from pathlib import Path
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from chatbot.config import settings
from chatbot.graph import get_chatbot
from database.session import get_sqlite_connection

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def list_and_select_thread() -> str:
    """
    Connects to the SQLite checkpoint database, lists any existing conversation
    threads, and prompts the user to select one to resume or start a new session.
    """
    conn = get_sqlite_connection()
    
    try:
        # Fetch distinct threads stored in checkpoints table
        existing = conn.execute(
            "SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id"
        ).fetchall()
    except Exception:
        # Checkpoint table won't exist yet on clean databases
        existing = []
    finally:
        conn.close()

    print("\n" + "=" * 50)
    print("      LANGGRAPH AI ASSISTANT TERMINAL SESSION")
    print("=" * 50)
    
    if existing:
        print("\nExisting conversation sessions found:")
        for i, (tid,) in enumerate(existing, 1):
            print(f"  [{i}] Thread: {tid}")
        print("  [n] Start a brand new session")
        
        choice = input("\nSelect a thread number to resume or 'n' for new: ").strip().lower()
        if choice == "n" or not choice.isdigit():
            thread_id = str(uuid.uuid4())
            print(f"[*] Started new conversation thread: {thread_id}")
        else:
            idx = int(choice) - 1
            if 0 <= idx < len(existing):
                thread_id = existing[idx][0]
                print(f"[*] Resuming conversation thread: {thread_id}")
            else:
                thread_id = str(uuid.uuid4())
                print(f"[*] Invalid choice. Started new conversation thread: {thread_id}")
    else:
        thread_id = str(uuid.uuid4())
        print(f"[*] No previous sessions found. Started new thread: {thread_id}")
        
    print("=" * 50 + "\nType 'exit', 'quit', or 'bye' to end the chat.\n")
    return thread_id

def run_cli():
    """
    Main interactive loop for the CLI. Handles input reading, streaming,
    and resolving HITL approval interrupts directly from standard input.
    """
    if not settings:
        print("[ERROR] Cannot start CLI: Missing environment configuration. See .env.example.")
        return

    # Load thread selection
    thread_id = list_and_select_thread()
    
    # Load compiled graph
    chatbot = get_chatbot()
    
    # Run loop
    while True:
        try:
            user_query = input("Ask a query > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAI: Goodbye!")
            break

        if not user_query:
            continue

        if user_query.lower() in ["exit", "quit", "bye"]:
            print("AI: Goodbye! Hope you got answers.")
            break

        # Thread configuration
        config = {
            "configurable": {
                "thread_id": thread_id,
                "metadata": {"thread_id": thread_id},
                "run_name": "cli_chat_turn"
            }
        }

        # Initialize input query payload
        input_data = {"messages": [HumanMessage(content=user_query)]}
        print("AI > ", end="", flush=True)

        # Loop enables resuming streaming after HITL interrupts
        while True:
            interrupted = False

            # Stream both message tokens and update events
            for mode, data in chatbot.stream(
                input_data,
                config=config,
                stream_mode=["messages", "updates"]
            ):
                if mode == "messages":
                    chunk, _ = data
                    # Check if it has text content and isn't purely a tool call block
                    if (hasattr(chunk, "content") and 
                        chunk.content and 
                        not getattr(chunk, "tool_calls", None)):
                        print(chunk.content, end="", flush=True)

                elif mode == "updates":
                    for node_name, node_output in data.items():
                        if node_name == "__interrupt__":
                            # Handle Human-in-the-Loop Interrupt
                            interrupt_info = node_output[0].value
                            print(f"\n\n🔍 [HUMAN APPROVAL REQUIRED]")
                            print(f"   Tool Request: {interrupt_info.get('tool_name')}")
                            print(f"   Search Query: '{interrupt_info.get('query')}'")
                            
                            approval = ""
                            while approval not in ["yes", "no"]:
                                approval = input("   Approve this web search? (yes/no): ").strip().lower()

                            # Set up Command to resume graph execution with approval
                            input_data = Command(resume={"approved": approval})
                            interrupted = True
                            print("AI (resuming) > ", end="", flush=True)

            if not interrupted:
                break # Turn complete, no further interrupts

        print("\n")

if __name__ == "__main__":
    run_cli()
