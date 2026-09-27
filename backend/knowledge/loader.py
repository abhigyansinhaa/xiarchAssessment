from typing import Dict, Any, List, Optional
from backend.knowledge.sqlite_source import SQLiteKnowledgeSource
from backend.knowledge.json_source import JSONKnowledgeSource
from backend.knowledge.csv_source import CSVKnowledgeSource
from backend.knowledge.vector_source import VectorKnowledgeSource


class UnifiedKnowledgeManager:
    """
    Coordinates and indexes all 4 internal knowledge sources:
    1. SQLite Database: Structured employee profiles, managers, live leave records
    2. JSON Storage: Formal corporate policy registry
    3. CSV Files: Attendance logs and compensation payroll records
    4. ChromaDB Vector Store: Unstructured policy handbooks & guidelines
    """

    def __init__(self):
        self.sqlite = SQLiteKnowledgeSource()
        self.json_policies = JSONKnowledgeSource()
        self.csv_logs = CSVKnowledgeSource()
        self.vector_store = VectorKnowledgeSource()

    def get_source_manifest(self) -> Dict[str, Any]:
        return {
            "sources": [
                {
                    "name": "SQLite Central Database",
                    "type": "relational_db",
                    "authority_level": 1,
                    "description": "Primary authoritative database for employee profiles, org structure, leave balances, and leave transactions."
                },
                {
                    "name": "JSON Policy Registry",
                    "type": "structured_json",
                    "authority_level": 2,
                    "description": "Official company policies, eligibility guidelines, limits, and rules."
                },
                {
                    "name": "CSV Operations Logs",
                    "type": "tabular_csv",
                    "authority_level": 3,
                    "description": "Daily biometric attendance logs and monthly payroll disbursement statements."
                },
                {
                    "name": "ChromaDB Vector Store",
                    "type": "vector_embeddings",
                    "authority_level": 4,
                    "description": "Semantic knowledge base of full markdown policy documents and benefits handbooks."
                }
            ]
        }

    def detect_conflicts(self, employee_id: int, claimed_balance: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Cross-checks employee self-claimed or external information against authoritative SQLite records.
        Requirements: 'Handle incomplete or conflicting information gracefully.'
        """
        conflicts = []
        emp = self.sqlite.get_employee_by_id(employee_id)
        if not emp:
            return [{"type": "MISSING_RECORD", "message": f"Employee ID {employee_id} not found in central database."}]

        if claimed_balance is not None and claimed_balance != emp["remaining_annual_leave"]:
            conflicts.append({
                "type": "LEAVE_BALANCE_DISCREPANCY",
                "employee_name": emp["name"],
                "claimed_balance": claimed_balance,
                "authoritative_balance": emp["remaining_annual_leave"],
                "total_allocated": emp["total_annual_leave"],
                "recorded_used": emp["used_annual_leave"],
                "resolution_strategy": (
                    f"Authoritative SQLite database indicates {emp['remaining_annual_leave']} remaining days "
                    f"({emp['total_annual_leave']} allocated - {emp['used_annual_leave']} used). "
                    f"Employee claimed {claimed_balance} days. Per Policy POL-001 Section 4, SQLite is authoritative; "
                    "reconciliation ticket should be initiated with HR Operations desk."
                )
            })

        return conflicts


# Global singleton instance
knowledge_manager = UnifiedKnowledgeManager()
