import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import BASE_DIR, HOST, PORT
from backend.models.database import init_db
from backend.models.schemas import ChatRequest, ChatResponse, ApprovalActionRequest
from backend.agent.orchestrator import AgentOrchestrator
from backend.agent.executor import ActionExecutor, PENDING_APPROVAL_STORE
from backend.audit.logger import AuditLogger
from backend.agent.memory import memory_manager
from backend.knowledge.loader import knowledge_manager

# Ensure DB initialized
init_db()

app = FastAPI(
    title="Xiarch Bharat Autonomous AI Agent",
    description="Agentic AI with internal knowledge retrieval, ReAct reasoning, multi-step planning, and human-in-the-loop governance.",
    version="1.0.0"
)

# CORS middleware for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = AgentOrchestrator()
FRONTEND_DIR = BASE_DIR / "frontend"


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Xiarch Autonomous Agent",
        "knowledge_sources": 4,
        "human_approval_gate": True,
        "audit_logging": True
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        response = await orchestrator.process_query(
            user_query=request.message,
            session_id=request.session_id or "default-session"
        )
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pending-approvals")
async def get_pending_approvals():
    return {"pending_actions": list(PENDING_APPROVAL_STORE.values())}


@app.post("/api/approval")
async def handle_approval(payload: ApprovalActionRequest):
    if payload.approved:
        res = ActionExecutor.approve_and_execute(payload.action_id, payload.reason)
    else:
        res = ActionExecutor.reject_action(payload.action_id, payload.reason)

    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@app.get("/api/audit-logs")
async def get_audit_logs(limit: int = 50, session_id: str = None):
    logs = AuditLogger.get_recent_logs(limit=limit, session_id=session_id)
    return {"total": len(logs), "logs": logs}


@app.get("/api/memories")
async def get_memories(session_id: str = "global"):
    memories = memory_manager.get_all_memories(session_id=session_id)
    return {"memories": memories}


@app.get("/api/knowledge-sources")
async def get_knowledge_sources():
    return knowledge_manager.get_source_manifest()


# Mount frontend static files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
