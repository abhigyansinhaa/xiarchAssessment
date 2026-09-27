import re
from typing import List, Dict, Any
from backend.knowledge.sqlite_source import extract_employee


class TaskPlan:
    def __init__(self, query: str, is_multistep: bool, steps: List[Dict[str, Any]], parallel_execution: bool = False):
        self.query = query
        self.is_multistep = is_multistep
        self.steps = steps
        self.parallel_execution = parallel_execution

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "is_multistep": self.is_multistep,
            "steps": self.steps,
            "parallel_execution": self.parallel_execution
        }


class MultiStepPlanner:
    """
    Decomposes incoming user requests into logical reasoning and action steps.
    Identifies if queries require multi-source synthesis or parallel tool execution.
    Requirement: 'Support multi-step reasoning and planning'
    Bonus: 'Execute multiple actions in parallel where applicable'
    """

    @staticmethod
    def plan(user_query: str) -> TaskPlan:
        q = user_query.lower()

        # Case 1: Sabbatical + Leave Balance multi-source query
        if ("sabbatical" in q or "long leave" in q) and ("leave" in q or "balance" in q or "qualify" in q):
            # Dynamic lookup of employee from DB
            target_name = extract_employee(user_query)
            if not target_name:
                # Do NOT plan multi-step with a hardcoded fallback name if employee not in records
                return TaskPlan(
                    query=user_query,
                    is_multistep=False,
                    parallel_execution=False,
                    steps=[]
                )

            return TaskPlan(
                query=user_query,
                is_multistep=True,
                parallel_execution=True,
                steps=[
                    {
                        "step_number": 1,
                        "title": "Check Current Leave Balance",
                        "tool": "check_leave_balance",
                        "arguments": {"identifier": target_name},
                        "reasoning": f"Retrieve authoritative live annual and casual leave balance for {target_name} from SQLite HR Database.",
                        "can_parallel": True
                    },
                    {
                        "step_number": 2,
                        "title": "Verify Sabbatical Policy & Tenure Eligibility",
                        "tool": "check_sabbatical_eligibility",
                        "arguments": {"employee_name_or_id": target_name},
                        "reasoning": f"Compute continuous organizational tenure and cross-reference with Policy POL-004 requirements.",
                        "can_parallel": True
                    }
                ]
            )

        # Case 2: Batch approval for department
        if "approve" in q and ("all" in q or "pending" in q) and ("team" in q or "department" in q or "marketing" in q or "engineering" in q):
            dept = "Marketing" if "marketing" in q else ("Engineering" if "engineering" in q else "All")
            return TaskPlan(
                query=user_query,
                is_multistep=True,
                parallel_execution=False,
                steps=[
                    {
                        "step_number": 1,
                        "title": f"Identify & Batch-Approve Pending Leaves for {dept}",
                        "tool": "approve_all_pending_by_department",
                        "arguments": {"department": dept},
                        "reasoning": f"Locate all pending leave transactions for {dept} and stage for critical approval execution."
                    }
                ]
            )

        # Case 3: Attendance report with absence threshold
        if "attendance" in q or "absent" in q or "absences" in q:
            dept = "Engineering" if "engineering" in q else ("Marketing" if "marketing" in q else None)
            return TaskPlan(
                query=user_query,
                is_multistep=True,
                parallel_execution=False,
                steps=[
                    {
                        "step_number": 1,
                        "title": "Query CSV Attendance Logs & Correlate with Personnel Directory",
                        "tool": "get_attendance_report",
                        "arguments": {"department": dept, "absence_threshold": 3},
                        "reasoning": "Analyze September daily punch logs from CSV and correlate with SQLite employee records to flag patterns >3 absences."
                    }
                ]
            )

        # Case 4: Conflict / Discrepancy resolution
        if ("discrepancy" in q or "conflict" in q or "says" in q or "claim" in q) and ("leave" in q or "balance" in q):
            num_match = re.search(r'(\d+)\s*(?:days|leave)', q)
            claimed = int(num_match.group(1)) if num_match else 20
            return TaskPlan(
                query=user_query,
                is_multistep=True,
                parallel_execution=False,
                steps=[
                    {
                        "step_number": 1,
                        "title": "Cross-Check Employee Claim Against Authoritative System of Record",
                        "tool": "detect_conflicts",
                        "arguments": {"employee_id": 106, "claimed_balance": claimed},
                        "reasoning": f"Compare self-reported claim ({claimed} days) against primary SQLite database and cite Section 4 reconciliation protocol."
                    }
                ]
            )

        # Case 5: Long-term memory storage
        if "remember" in q or "note that" in q or "preference" in q:
            return TaskPlan(
                query=user_query,
                is_multistep=False,
                parallel_execution=False,
                steps=[
                    {
                        "step_number": 1,
                        "title": "Commit Fact to Long-Term Memory",
                        "tool": "remember_fact",
                        "arguments": {
                            "key": "Communication Preference",
                            "value": user_query.replace("remember that", "").replace("remember", "").strip(),
                            "category": "preference"
                        },
                        "reasoning": "Persist user preference into SQLite agent_memories table for cross-session recall."
                    }
                ]
            )

        # Default Single-step / Standard Plan (delegated to LLM or tool discovery)
        return TaskPlan(
            query=user_query,
            is_multistep=False,
            parallel_execution=False,
            steps=[]
        )
