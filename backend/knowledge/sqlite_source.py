from typing import List, Dict, Any, Optional
from sqlalchemy import or_
from backend.models.database import SessionLocal, Employee, LeaveRequest


class SQLiteKnowledgeSource:
    """Retrieves and queries structured employee and leave data from SQLite DB."""

    def __init__(self):
        self.source_name = "SQLite Central DB (HR Database)"

    def search_employees(self, query: str = "", department: Optional[str] = None) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            q = db.query(Employee)
            if query:
                pattern = f"%{query.strip()}%"
                filters = [
                    Employee.name.ilike(pattern),
                    Employee.email.ilike(pattern),
                    Employee.role.ilike(pattern),
                    Employee.department.ilike(pattern)
                ]
                words = [w for w in query.strip().split() if len(w) >= 3]
                for w in words:
                    filters.append(Employee.name.ilike(f"%{w}%"))

                q = q.filter(or_(*filters))
            if department:
                q = q.filter(Employee.department.ilike(f"%{department}%"))

            employees = q.all()
            # Sort with exact or prefix name match prioritized
            q_clean = query.strip().lower()
            def rank_emp(emp):
                ename = emp.name.lower()
                if ename == q_clean:
                    return 0
                if ename.startswith(q_clean):
                    return 1
                if q_clean in ename:
                    return 2
                return 3

            sorted_emps = sorted(employees, key=rank_emp)
            return [emp.to_dict() for emp in sorted_emps]
        finally:
            db.close()

    def get_employee_by_id(self, employee_id: int) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == employee_id).first()
            return emp.to_dict() if emp else None
        finally:
            db.close()

    def get_employee_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            pattern = f"%{name.strip()}%"
            emp = db.query(Employee).filter(Employee.name.ilike(pattern)).first()
            return emp.to_dict() if emp else None
        finally:
            db.close()

    def get_leave_balance(self, employee_id: int) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == employee_id).first()
            if not emp:
                return None
            return {
                "employee_id": emp.id,
                "name": emp.name,
                "department": emp.department,
                "total_annual_leave": emp.total_annual_leave,
                "used_annual_leave": emp.used_annual_leave,
                "remaining_annual_leave": emp.remaining_annual_leave,
                "sick_leave_balance": emp.sick_leave_balance,
                "casual_leave_balance": emp.casual_leave_balance
            }
        finally:
            db.close()

    def list_pending_leave_requests(self, department: Optional[str] = None) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            q = db.query(LeaveRequest).filter(LeaveRequest.status == "PENDING")
            if department:
                q = q.join(Employee).filter(Employee.department.ilike(f"%{department}%"))
            requests = q.all()
            return [r.to_dict() for r in requests]
        finally:
            db.close()

    def list_all_leave_requests(self, employee_id: Optional[int] = None) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            q = db.query(LeaveRequest)
            if employee_id:
                q = q.filter(LeaveRequest.employee_id == employee_id)
            requests = q.order_by(LeaveRequest.created_at.desc()).all()
            return [r.to_dict() for r in requests]
        finally:
            db.close()
