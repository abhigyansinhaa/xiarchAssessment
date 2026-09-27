import json
import datetime
from typing import Dict, Any, Optional, List
from backend.models.database import SessionLocal, AuditLog
from backend.config import AUDIT_LOG_ENABLED


class AuditLogger:
    @staticmethod
    def log_action(
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Any,
        reasoning: str,
        session_id: str = "default",
        user_request: Optional[str] = None,
        status: str = "SUCCESS",
        requires_approval: bool = False,
        approval_status: str = "NOT_REQUIRED"
    ) -> int:
        if not AUDIT_LOG_ENABLED:
            return 0

        db = SessionLocal()
        try:
            input_str = json.dumps(tool_input, default=str)
            output_str = json.dumps(tool_output, default=str) if not isinstance(tool_output, str) else tool_output

            entry = AuditLog(
                timestamp=datetime.datetime.utcnow(),
                session_id=session_id,
                user_request=user_request,
                tool_name=tool_name,
                tool_input=input_str,
                tool_output=output_str,
                status=status,
                reasoning=reasoning,
                requires_approval=requires_approval,
                approval_status=approval_status
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry.id
        except Exception as e:
            print(f"[AuditLogger] Logging error: {e}")
            return 0
        finally:
            db.close()

    @staticmethod
    def get_recent_logs(limit: int = 50, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            q = db.query(AuditLog)
            if session_id:
                q = q.filter(AuditLog.session_id == session_id)
            logs = q.order_by(AuditLog.timestamp.desc()).limit(limit).all()
            return [l.to_dict() for l in logs]
        finally:
            db.close()

    @staticmethod
    def update_approval_status(log_id: int, new_status: str, notes: Optional[str] = None) -> bool:
        db = SessionLocal()
        try:
            entry = db.query(AuditLog).filter(AuditLog.id == log_id).first()
            if entry:
                entry.approval_status = new_status
                entry.status = "SUCCESS" if new_status == "APPROVED" else "REJECTED"
                if notes:
                    entry.reasoning = (entry.reasoning or "") + f" [Human Decision: {notes}]"
                db.commit()
                return True
            return False
        finally:
            db.close()
