from typing import List, Dict, Any, Optional
from backend.models.database import SessionLocal, Employee
from backend.knowledge.loader import knowledge_manager


class EmployeeService:
    @staticmethod
    def search_employees(query: str = "", department: Optional[str] = None) -> List[Dict[str, Any]]:
        return knowledge_manager.sqlite.search_employees(query, department)

    @staticmethod
    def get_employee(identifier: str) -> Optional[Dict[str, Any]]:
        # Check if integer ID
        if str(identifier).strip().isdigit():
            return knowledge_manager.sqlite.get_employee_by_id(int(identifier))
        return knowledge_manager.sqlite.get_employee_by_name(identifier)

    @staticmethod
    def update_employee(employee_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == employee_id).first()
            if not emp:
                return {"error": f"Employee {employee_id} not found"}

            allowed_fields = ["name", "email", "role", "department", "status", "location", "manager_id", "manager_name"]
            changed = {}
            for k, v in updates.items():
                if k in allowed_fields and v is not None:
                    setattr(emp, k, v)
                    changed[k] = v

            db.commit()
            db.refresh(emp)
            return {"success": True, "employee": emp.to_dict(), "updated_fields": changed}
        finally:
            db.close()
