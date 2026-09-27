from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User query or command for the agent")
    session_id: Optional[str] = Field("default-session", description="Session ID for memory & history")
    stream: Optional[bool] = Field(False, description="Whether to stream response")


class ApprovalActionRequest(BaseModel):
    action_id: str = Field(..., description="Action ID requiring approval")
    approved: bool = Field(..., description="Whether human approved the action")
    reason: Optional[str] = Field(None, description="Optional reason for approval or rejection")


class ToolCallLog(BaseModel):
    tool: str
    arguments: Dict[str, Any]
    output: Any
    critical: bool = False
    requires_approval: bool = False
    approval_status: Optional[str] = None
    reasoning: Optional[str] = None
    duration_ms: Optional[float] = None


class ReasoningStep(BaseModel):
    step_number: int
    title: str
    detail: str
    source_used: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    reasoning_summary: str
    reasoning_steps: List[ReasoningStep] = []
    actions_taken: List[ToolCallLog] = []
    sources_consulted: List[str] = []
    pending_approvals: List[Dict[str, Any]] = []
    conflicts_detected: List[str] = []
    session_id: str


class MemoryItem(BaseModel):
    key: str
    value: str
    category: str = "general"
