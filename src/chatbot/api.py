import json
import logging
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from chatbot.config import settings, BASE_DIR
from chatbot.graph import get_chatbot
from database.session import get_sqlite_connection
from services.rag_service import index_document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="LangGraph AI Assistant API",
    description="Production-grade API backend managing LangGraph agents, multi-threading state, RAG indexers, and Human-in-the-Loop gates.",
    version="1.0.0"
)

# Enable CORS for React Frontend (Vite defaults to localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic Request/Response Models ──────────────────────────────────────
class ChatRequest(BaseModel):
    thread_id: str
    message: str

class ApprovalRequest(BaseModel):
    thread_id: str
    approved: str # "yes" or "no"

class GeneralResponse(BaseModel):
    status: str
    message: str

# ── Helper Functions ──────────────────────────────────────────────────────
def get_db_connection():
    return get_sqlite_connection()

# ── API Endpoints ─────────────────────────────────────────────────────────

@app.get("/api/status", response_model=GeneralResponse)
def get_status():
    """Checks the server status and API configurations."""
    if not settings:
        return {"status": "error", "message": "Environment settings failed to load."}
    
    pdf_exists = settings.abs_pdf_path.exists()
    return {
        "status": "online",
        "message": f"Service active. RAG PDF File Present: {pdf_exists}"
    }

@app.get("/api/threads")
def list_threads():
    """Retrieves all active conversation thread IDs from SQLite checkpoints."""
    conn = get_db_connection()
    
    try:
        cursor = conn.execute("SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id")
        threads = [row[0] for row in cursor.fetchall()]
        return {"threads": threads}
    except Exception as e:
        logger.error(f"Error fetching threads from DB (%s): %s", db_path, e, exc_info=True)
        return {"threads": []}
    finally:
        conn.close()

@app.post("/api/index", response_model=GeneralResponse)
def trigger_rag_indexing(background_tasks: BackgroundTasks):
    """Triggers the document vector store indexing in the background."""
    logger.info("Manual RAG indexing requested.")
    
    # Run indexing synchronously or in background
    res = index_document()
    if res["status"] == "error":
        raise HTTPException(status_code=500, detail=res["message"])
        
    return {"status": "success", "message": res["message"]}

@app.get("/api/pdf/{filename}")
def download_pdf(filename: str):
    """Serves the generated productivity schedule PDF files for download."""
    data_dir = settings.abs_output_path if settings else BASE_DIR / Path("data/output")
    pdf_path = data_dir / filename
    
    # Prevent path traversal
    if not pdf_path.resolve().is_relative_to(data_dir.resolve()):
         raise HTTPException(status_code=400, detail="Invalid file path operation.")
         
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file '{filename}' not found.")
        
    return FileResponse(
        path=str(pdf_path),
        filename=filename,
        media_type="application/pdf"
    )

@app.post("/api/chat")
async def chat_stream(req: ChatRequest):
    """
    Accepts conversation messages and streams real-time token events and tool executions
    using Server-Sent Events (SSE).
    """
    chatbot = get_chatbot()
    
    config = {
        "configurable": {
            "thread_id": req.thread_id,
            "metadata": {"thread_id": req.thread_id},
            "run_name": "web_chat_turn"
        }
    }

    # Initialize graph input message payload
    input_data = {"messages": [HumanMessage(content=req.message)]}

    async def event_generator():
        try:
            # We wrap the synchronous generator chatbot.stream in an async-friendly queue
            # to prevent blocking the async FastAPI event loop.
            loop = asyncio.get_event_loop()
            
            def sync_stream():
                return chatbot.stream(
                    input_data,
                    config=config,
                    stream_mode=["messages", "updates"]
                )
                
            # Running synchronous streaming in an executor thread
            stream = await loop.run_in_executor(None, sync_stream)
            
            for mode, data in stream:
                if mode == "messages":
                    chunk, _ = data
                    # Stream tokens in real time
                    if (hasattr(chunk, "content") and 
                        chunk.content and 
                        not getattr(chunk, "tool_calls", None)):
                        
                        yield f"data: {json.dumps({'event': 'token', 'text': chunk.content})}\n\n"
                        await asyncio.sleep(0.01) # Yield execution control to client
                        
                elif mode == "updates":
                    for node_name, node_output in data.items():
                        if node_name == "__interrupt__":
                            # Handle Human-in-the-Loop interruption and yield approval payload
                            interrupt_info = node_output[0].value
                            yield f"data: {json.dumps({'event': 'interrupt', 'tool_name': interrupt_info.get('tool_name'), 'query': interrupt_info.get('query')})}\n\n"
                            return # Terminate stream, wait for approval response
                            
                        # Capture tool start and end events for UI visualization
                        elif node_name == "tools":
                            # Output logs for tool executions
                            logger.info(f"Tool executed. Node output: {node_output}")
                            yield f"data: {json.dumps({'event': 'tool_end', 'node': node_name, 'output': str(node_output)})}\n\n"
                        
                        elif node_name == "chat_node":
                            # Capture chat responses and update structures
                            logger.info("Chat Node executed.")

            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in stream generator: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/approve")
async def resolve_approval(req: ApprovalRequest):
    """
    Submits human reviewer's approval (yes/no) to resolve the pending search interrupt
    and resumes streaming graph execution.
    """
    chatbot = get_chatbot()
    
    config = {
        "configurable": {
            "thread_id": req.thread_id,
            "metadata": {"thread_id": req.thread_id},
            "run_name": "web_approval_resume"
        }
    }

    # Resume command payload
    resume_command = Command(resume={"approved": req.approved.strip().lower()})

    async def resume_generator():
        try:
            loop = asyncio.get_event_loop()
            
            def sync_resume():
                return chatbot.stream(
                    resume_command,
                    config=config,
                    stream_mode=["messages", "updates"]
                )
                
            stream = await loop.run_in_executor(None, sync_resume)
            
            for mode, data in stream:
                if mode == "messages":
                    chunk, _ = data
                    if (hasattr(chunk, "content") and 
                        chunk.content and 
                        not getattr(chunk, "tool_calls", None)):
                        
                        yield f"data: {json.dumps({'event': 'token', 'text': chunk.content})}\n\n"
                        await asyncio.sleep(0.01)
                        
                elif mode == "updates":
                    for node_name, node_output in data.items():
                        if node_name == "__interrupt__":
                            interrupt_info = node_output[0].value
                            yield f"data: {json.dumps({'event': 'interrupt', 'tool_name': interrupt_info.get('tool_name'), 'query': interrupt_info.get('query')})}\n\n"
                            return
                        elif node_name == "tools":
                            yield f"data: {json.dumps({'event': 'tool_end', 'node': node_name, 'output': str(node_output)})}\n\n"

            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            
        except Exception as e:
            logger.error(f"Error resuming graph execution: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(resume_generator(), media_type="text/event-stream")

@app.get("/api/token-budget")
async def get_token_budget():
    max_tokens = settings.MAX_TOKEN_BUDGET if settings else 150
    return {
        "token_budget": max_tokens
    }

# ── Entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
