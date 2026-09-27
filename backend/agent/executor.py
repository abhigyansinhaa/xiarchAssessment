import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from backend.agent.tools import execute_tool, CRITICAL_TOOLS, TOOL_SOURCE_MAP
from backend.audit.logger import AuditLogger
from backend.config import ENABLE_HUMAN_APPROVAL

# In-memory registry for pending approval actions
# action_id -> { "action_id", "tool_name", "arguments", "reasoning", "session_id", "user_request", "created_at" }
PENDING_APPROVAL_STORE: Dict[str, Dict[str, Any]] = {}


class ActionExecutor:
    """
    Executes actions with:
    - Human approval gate for critical/irreversible actions
    - Parallel execution via asyncio for multi-action scenarios
    - Structured audit logging
    - Explainability & duration tracking
    """

    @staticmethod
    def is_critical(tool_name: str) -> bool:
        return tool_name in CRITICAL_TOOLS

    @staticmethod
    def stage_or_execute(
        tool_name: str,
        arguments: Dict[str, Any],
        reasoning: str,
        session_id: str = "default",
        user_request: Optional[str] = None,
        force_execute: bool = False
    ) -> Dict[str, Any]:
        critical = ActionExecutor.is_critical(tool_name)

        # Check if human approval is required and not forced
        if critical and ENABLE_HUMAN_APPROVAL and not force_execute:
            action_id = f"act_{uuid.uuid4().hex[:8]}"
            pending_item = {
                "action_id": action_id,
                "tool_name": tool_name,
                "arguments": arguments,
                "reasoning": reasoning,
                "description": CRITICAL_TOOLS.get(tool_name, "Critical action"),
                "session_id": session_id,
                "user_request": user_request,
                "created_at": time.time(),
                "source": TOOL_SOURCE_MAP.get(tool_name, "Internal Database")
            }
            PENDING_APPROVAL_STORE[action_id] = pending_item

            log_id = AuditLogger.log_action(
                tool_name=tool_name,
                tool_input=arguments,
                tool_output="Staged awaiting human approval",
                reasoning=reasoning,
                session_id=session_id,
                user_request=user_request,
                status="PENDING_APPROVAL",
                requires_approval=True,
                approval_status="PENDING"
            )
            pending_item["audit_log_id"] = log_id

            return {
                "tool": tool_name,
                "arguments": arguments,
                "output": {
                    "status": "AWAITING_HUMAN_APPROVAL",
                    "action_id": action_id,
                    "action_description": CRITICAL_TOOLS.get(tool_name),
                    "message": f"This action modifies internal state and requires your confirmation before execution."
                },
                "critical": True,
                "requires_approval": True,
                "action_id": action_id,
                "reasoning": reasoning,
                "source": TOOL_SOURCE_MAP.get(tool_name, "Internal DB")
            }

        # Otherwise execute immediately
        start_time = time.time()
        try:
            output = execute_tool(tool_name, arguments, session_id=session_id)
            elapsed_ms = round((time.time() - start_time) * 1000, 2)

            AuditLogger.log_action(
                tool_name=tool_name,
                tool_input=arguments,
                tool_output=output,
                reasoning=reasoning,
                session_id=session_id,
                user_request=user_request,
                status="SUCCESS",
                requires_approval=critical,
                approval_status="APPROVED" if critical else "NOT_REQUIRED"
            )

            return {
                "tool": tool_name,
                "arguments": arguments,
                "output": output,
                "critical": critical,
                "requires_approval": False,
                "reasoning": reasoning,
                "duration_ms": elapsed_ms,
                "source": TOOL_SOURCE_MAP.get(tool_name, "Internal Knowledge")
            }
        except Exception as e:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            AuditLogger.log_action(
                tool_name=tool_name,
                tool_input=arguments,
                tool_output=str(e),
                reasoning=reasoning,
                session_id=session_id,
                user_request=user_request,
                status="FAILED",
                requires_approval=critical,
                approval_status="FAILED"
            )
            return {
                "tool": tool_name,
                "arguments": arguments,
                "output": {"error": str(e)},
                "critical": critical,
                "requires_approval": False,
                "reasoning": reasoning,
                "duration_ms": elapsed_ms,
                "source": TOOL_SOURCE_MAP.get(tool_name, "Internal Knowledge")
            }

    @staticmethod
    def approve_and_execute(action_id: str, approver_reason: Optional[str] = None) -> Dict[str, Any]:
        """Called when a user confirms an approval in the UI modal or API."""
        item = PENDING_APPROVAL_STORE.pop(action_id, None)
        if not item:
            return {"error": f"No pending action found with ID: {action_id}"}

        tool_name = item["tool_name"]
        arguments = item["arguments"]
        session_id = item["session_id"]
        audit_log_id = item.get("audit_log_id")

        start_time = time.time()
        output = execute_tool(tool_name, arguments, session_id=session_id)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        if audit_log_id:
            AuditLogger.update_approval_status(audit_log_id, "APPROVED", approver_reason or "Approved by Human Operator")

        return {
            "success": True,
            "action_id": action_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "output": output,
            "duration_ms": elapsed_ms
        }

    @staticmethod
    def reject_action(action_id: str, rejection_reason: Optional[str] = None) -> Dict[str, Any]:
        item = PENDING_APPROVAL_STORE.pop(action_id, None)
        if not item:
            return {"error": f"No pending action found with ID: {action_id}"}

        audit_log_id = item.get("audit_log_id")
        if audit_log_id:
            AuditLogger.update_approval_status(audit_log_id, "REJECTED", rejection_reason or "Cancelled by Human Operator")

        return {
            "success": True,
            "action_id": action_id,
            "status": "REJECTED",
            "message": f"Action {item['tool_name']} was cancelled by human approval policy."
        }

    @staticmethod
    async def execute_parallel(tool_calls: List[Dict[str, Any]], session_id: str, user_request: str) -> List[Dict[str, Any]]:
        """
        Executes multiple tool calls concurrently using asyncio.
        Bonus Requirement: 'Execute multiple actions in parallel where applicable'
        """
        loop = asyncio.get_event_loop()
        tasks = []
        for call in tool_calls:
            task = loop.run_in_executor(
                None,
                ActionExecutor.stage_or_execute,
                call["tool"],
                call["arguments"],
                call.get("reasoning", "Parallel sub-task execution"),
                session_id,
                user_request,
                False
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return list(results)
