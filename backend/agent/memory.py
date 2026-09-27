from typing import List, Dict, Any, Optional
from backend.models.database import SessionLocal, AgentMemory


class LongTermMemoryManager:
    """
    Manages cross-session and intra-session long-term memory for the autonomous agent.
    Allows user preferences, custom notes, and organizational constraints to persist.
    Requirement: 'Add long-term memory'
    """

    def remember(self, key: str, value: str, category: str = "preference", session_id: str = "global") -> Dict[str, Any]:
        db = SessionLocal()
        try:
            mem = (
                db.query(AgentMemory)
                .filter(AgentMemory.session_id == session_id, AgentMemory.memory_key.ilike(key.strip()))
                .first()
            )
            if mem:
                mem.memory_value = value
                mem.category = category
            else:
                mem = AgentMemory(
                    session_id=session_id,
                    memory_key=key.strip(),
                    memory_value=value,
                    category=category
                )
                db.add(mem)

            db.commit()
            db.refresh(mem)
            return {"success": True, "memory": mem.to_dict()}
        finally:
            db.close()

    def recall(self, query: str = "", session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            q = db.query(AgentMemory)
            if session_id and session_id != "global":
                q = q.filter((AgentMemory.session_id == session_id) | (AgentMemory.session_id == "global"))
            if query:
                pattern = f"%{query}%"
                q = q.filter(
                    (AgentMemory.memory_key.ilike(pattern)) | (AgentMemory.memory_value.ilike(pattern))
                )
            memories = q.order_by(AgentMemory.updated_at.desc()).all()
            return [m.to_dict() for m in memories]
        finally:
            db.close()

    def get_all_memories(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.recall("", session_id)

    def format_memory_context(self, session_id: str = "global") -> str:
        memories = self.get_all_memories(session_id)
        if not memories:
            return ""

        lines = ["=== PERMANENT LONG-TERM MEMORY FACTS ==="]
        for m in memories:
            lines.append(f"- [{m['category'].upper()}] {m['memory_key']}: {m['memory_value']}")
        lines.append("=========================================")
        return "\n".join(lines)


# Global singleton
memory_manager = LongTermMemoryManager()
