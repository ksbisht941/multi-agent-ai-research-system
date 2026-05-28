import sys
import argparse
import uvicorn
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description="Unified entrypoint for the Production-Grade LangGraph AI Assistant Platform."
    )
    parser.add_argument(
        "mode",
        choices=["cli", "api", "index"],
        help="Execution mode: 'cli' runs the terminal assistant, 'api' starts the FastAPI server, 'index' runs RAG database document indexing."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="FastAPI host address (defaults to 127.0.0.1)."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="FastAPI port number (defaults to 8000)."
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload for API server development."
    )

    args = parser.parse_args()

    # Add src to python path to resolve chatbot imports correctly
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

    if args.mode == "cli":
        from chatbot.cli import run_cli
        run_cli()
        
    elif args.mode == "index":
        from chatbot.tools.rag import index_document
        print("[*] Launching RAG Indexer...")
        res = index_document()
        if res["status"] == "success":
            print(f"[+] Indexing Succeeded: {res['message']}")
        else:
            print(f"[-] Indexing Failed: {res['message']}")
            
    elif args.mode == "api":
        print(f"[*] Starting FastAPI uvicorn server at http://{args.host}:{args.port}")
        uvicorn.run(
            "chatbot.api:app",
            host=args.host,
            port=args.port,
            reload=args.reload
        )

if __name__ == "__main__":
    main()
