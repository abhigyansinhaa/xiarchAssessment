import json
from typing import Dict, Any, List, Optional
from backend.services.employee_service import EmployeeService
from backend.services.leave_service import LeaveService
from backend.services.policy_service import PolicyService
from backend.services.attendance_service import AttendanceService
from backend.knowledge.loader import knowledge_manager
from backend.agent.memory import memory_manager

# Critical actions that require explicit human approval before live execution
CRITICAL_TOOLS = {
    "submit_leave_request": "Creates a legally binding employee leave request",
    "approve_leave_request": "Formally approves employee leave and deducts leave balance",
    "reject_leave_request": "Formally rejects an employee leave request",
    "approve_all_pending_by_department": "Batch approves all pending employee leaves in a department",
    "update_employee_info": "Modifies sensitive official employee personnel records"
}

# Source mapping for provenance attribution in UI
TOOL_SOURCE_MAP = {
    "search_employees": "SQLite DB",
    "get_employee_details": "SQLite DB",
    "check_leave_balance": "SQLite DB",
    "search_policies": "JSON Policies",
    "semantic_search_policies": "ChromaDB Vector Store",
    "check_sabbatical_eligibility": "SQLite + JSON Policies + Vector Store",
    "get_attendance_report": "Attendance CSV + SQLite DB",
    "get_payroll_summary": "Payroll CSV",
    "detect_conflicts": "SQLite DB vs Claimed Input",
    "remember_fact": "Long-Term Memory",
    "recall_memory": "Long-Term Memory",
    "submit_leave_request": "SQLite DB (State Mutation)",
    "approve_leave_request": "SQLite DB (State Mutation)",
    "reject_leave_request": "SQLite DB (State Mutation)",
    "approve_all_pending_by_department": "SQLite DB (Batch Mutation)",
    "update_employee_info": "SQLite DB (State Mutation)"
}

# OpenAI Tool Specifications (Function calling schema)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_employees",
            "description": "Search the internal SQLite employee database by name, role, or department.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Name, role, or keyword to search for (e.g. 'Priya', 'Engineering')"
                    },
                    "department": {
                        "type": "string",
                        "description": "Optional department filter (e.g. 'Engineering', 'Marketing')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_employee_details",
            "description": "Get complete detailed personnel profile for an employee by name or ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "Employee ID or name (e.g. '105' or 'Amit Patel')"
                    }
                },
                "required": ["identifier"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_leave_balance",
            "description": "Retrieve current annual, medical, and casual leave quotas and used balances for an employee.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "Employee name or ID (e.g. 'Rahul' or '102')"
                    }
                },
                "required": ["identifier"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_policies",
            "description": "Search company policies stored in JSON registry by keyword or category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword to search policies for (e.g. 'remote work', 'annual leave', 'travel')"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter: 'leave', 'workplace', 'benefits', 'finance'"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search_policies",
            "description": "Perform natural language vector semantic search across full policy documents and handbooks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query about policies, guidelines, or procedures (e.g. 'Can I work from home on Friday?')"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of relevant sections to retrieve (default: 3)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_sabbatical_eligibility",
            "description": "Multi-source reasoning tool that checks if an employee meets tenure and performance criteria for sabbatical leave.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_name_or_id": {
                        "type": "string",
                        "description": "Employee name or ID (e.g. 'Amit Patel' or '105')"
                    }
                },
                "required": ["employee_name_or_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_attendance_report",
            "description": "Query CSV attendance logs and identify employees with high absenteeism or irregularities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Optional department filter (e.g. 'Engineering')"
                    },
                    "absence_threshold": {
                        "type": "integer",
                        "description": "Flag employees with absences greater than or equal to this number (default: 3)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_payroll_summary",
            "description": "Query CSV payroll statements for department compensation and payout totals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Department name or leave empty for company-wide"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_conflicts",
            "description": "Resolve discrepancies between an employee's verbal claim and authoritative database records.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "integer",
                        "description": "Employee ID (e.g. 106)"
                    },
                    "claimed_balance": {
                        "type": "integer",
                        "description": "The leave balance claimed by the employee (e.g. 20)"
                    }
                },
                "required": ["employee_id", "claimed_balance"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "Store a persistent fact, preference, or constraint in long-term memory across sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Subject or memory key (e.g. 'Neha communication preference')"
                    },
                    "value": {
                        "type": "string",
                        "description": "Information to remember (e.g. 'Prefers email communication over phone/Slack')"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category such as 'preference', 'fact', 'rule'"
                    }
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Retrieve stored facts or preferences from long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword or subject to recall"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_leave_request",
            "description": "Submit an official leave request into SQLite. [CRITICAL ACTION - Modifies legal leave ledger]",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_name_or_id": {
                        "type": "string",
                        "description": "Employee name or ID"
                    },
                    "leave_type": {
                        "type": "string",
                        "description": "Type of leave: 'Annual', 'Medical', 'Casual', 'Sabbatical'"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (e.g. '2026-10-01')"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (e.g. '2026-10-05')"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the leave request"
                    }
                },
                "required": ["employee_name_or_id", "leave_type", "start_date", "end_date", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "approve_leave_request",
            "description": "Formally approve an employee leave request and deduct annual leave balance. [CRITICAL ACTION]",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "integer",
                        "description": "The ID of the leave request to approve (e.g. 3)"
                    },
                    "approver_notes": {
                        "type": "string",
                        "description": "Optional notes or approval remarks"
                    }
                },
                "required": ["request_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reject_leave_request",
            "description": "Formally reject an employee leave request. [CRITICAL ACTION]",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "integer",
                        "description": "The ID of the leave request to reject"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for rejection"
                    }
                },
                "required": ["request_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "approve_all_pending_by_department",
            "description": "Batch approve all pending leave requests for an entire department. [CRITICAL ACTION - Batch operation]",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Department name (e.g. 'Marketing', 'Engineering')"
                    }
                },
                "required": ["department"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_employee_info",
            "description": "Update personnel data (role, department, manager, location) for an employee. [CRITICAL ACTION]",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "integer",
                        "description": "Employee ID to update"
                    },
                    "updates": {
                        "type": "object",
                        "description": "Key-value dictionary of fields to update (e.g. {'role': 'Staff Engineer'})"
                    }
                },
                "required": ["employee_id", "updates"]
            }
        }
    }
]


def execute_tool(tool_name: str, arguments: Dict[str, Any], session_id: str = "global") -> Any:
    """Dispatches a tool call to the corresponding internal service."""
    if tool_name == "search_employees":
        return EmployeeService.search_employees(
            query=arguments.get("query", ""),
            department=arguments.get("department")
        )

    elif tool_name == "get_employee_details":
        return EmployeeService.get_employee(str(arguments.get("identifier", "")))

    elif tool_name == "check_leave_balance":
        return LeaveService.get_leave_balance(str(arguments.get("identifier", "")))

    elif tool_name == "search_policies":
        return PolicyService.search_policies(
            query=arguments.get("query", ""),
            category=arguments.get("category")
        )

    elif tool_name == "semantic_search_policies":
        return PolicyService.semantic_policy_search(
            query=arguments.get("query", ""),
            top_k=int(arguments.get("top_k", 3))
        )

    elif tool_name == "check_sabbatical_eligibility":
        return PolicyService.check_sabbatical_eligibility(
            employee_name_or_id=str(arguments.get("employee_name_or_id", ""))
        )

    elif tool_name == "get_attendance_report":
        return AttendanceService.get_attendance_report(
            department=arguments.get("department"),
            absence_threshold=int(arguments.get("absence_threshold", 3))
        )

    elif tool_name == "get_payroll_summary":
        return AttendanceService.get_payroll_summary(
            department=arguments.get("department")
        )

    elif tool_name == "detect_conflicts":
        return knowledge_manager.detect_conflicts(
            employee_id=int(arguments.get("employee_id")),
            claimed_balance=arguments.get("claimed_balance")
        )

    elif tool_name == "remember_fact":
        return memory_manager.remember(
            key=arguments.get("key", ""),
            value=arguments.get("value", ""),
            category=arguments.get("category", "preference"),
            session_id=session_id
        )

    elif tool_name == "recall_memory":
        return memory_manager.recall(
            query=arguments.get("query", ""),
            session_id=session_id
        )

    elif tool_name == "submit_leave_request":
        return LeaveService.submit_leave_request(
            employee_name_or_id=arguments.get("employee_name_or_id", ""),
            leave_type=arguments.get("leave_type", "Annual"),
            start_date=arguments.get("start_date", ""),
            end_date=arguments.get("end_date", ""),
            reason=arguments.get("reason", "")
        )

    elif tool_name == "approve_leave_request":
        return LeaveService.approve_leave_request(
            request_id=int(arguments.get("request_id")),
            approver_notes=arguments.get("approver_notes")
        )

    elif tool_name == "reject_leave_request":
        return LeaveService.reject_leave_request(
            request_id=int(arguments.get("request_id")),
            reason=arguments.get("reason")
        )

    elif tool_name == "approve_all_pending_by_department":
        return LeaveService.approve_all_pending_by_department(
            department=arguments.get("department", "")
        )

    elif tool_name == "update_employee_info":
        return EmployeeService.update_employee(
            employee_id=int(arguments.get("employee_id")),
            updates=arguments.get("updates", {})
        )

    else:
        return {"error": f"Unknown tool: {tool_name}"}
