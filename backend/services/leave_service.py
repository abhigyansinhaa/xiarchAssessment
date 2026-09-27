import datetime
from typing import Dict, Any, List, Optional
from backend.models.database import SessionLocal, Employee, LeaveRequest
from backend.knowledge.loader import knowledge_manager


class LeaveService:
    @staticmethod
    def get_leave_balance(identifier: str) -> Dict[str, Any]:
        emp = None
        if str(identifier).strip().isdigit():
            emp = knowledge_manager.sqlite.get_employee_by_id(int(identifier))
        else:
            emp = knowledge_manager.sqlite.get_employee_by_name(identifier)

        if not emp:
            return {"error": f"Employee '{identifier}' not found in HR Database."}

        return {
            "employee_id": emp["id"],
            "name": emp["name"],
            "department": emp["department"],
            "remaining_annual_leave": emp["remaining_annual_leave"],
            "total_annual_leave": emp["total_annual_leave"],
            "used_annual_leave": emp["used_annual_leave"],
            "sick_leave_balance": emp["sick_leave_balance"],
            "casual_leave_balance": emp["casual_leave_balance"]
        }

    @staticmethod
    def submit_leave_request(
        employee_name_or_id: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        reason: str
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            if str(employee_name_or_id).strip().isdigit():
                emp = db.query(Employee).filter(Employee.id == int(employee_name_or_id)).first()
            else:
                emp = db.query(Employee).filter(Employee.name.ilike(f"%{employee_name_or_id.strip()}%")).first()

            if not emp:
                return {"error": f"Employee '{employee_name_or_id}' not found."}

            try:
                s_date = datetime.date.fromisoformat(start_date)
                e_date = datetime.date.fromisoformat(end_date)
            except ValueError:
                # Default to today if invalid format
                s_date = datetime.date.today()
                e_date = s_date

            days = max(1, (e_date - s_date).days + 1)

            # Check balance
            ltype_lower = leave_type.lower()
            if "annual" in ltype_lower or "vacation" in ltype_lower or "paid" in ltype_lower:
                leave_cat = "Annual"
                if emp.remaining_annual_leave < days:
                    return {
                        "error": (
                            f"Insufficient leave balance. Requested {days} days, "
                            f"but {emp.name} only has {emp.remaining_annual_leave} annual leave days remaining."
                        )
                    }
            elif "sick" in ltype_lower or "medical" in ltype_lower:
                leave_cat = "Medical"
            elif "casual" in ltype_lower:
                leave_cat = "Casual"
            elif "sabbatical" in ltype_lower:
                leave_cat = "Sabbatical"
            else:
                leave_cat = leave_type.title()

            new_req = LeaveRequest(
                employee_id=emp.id,
                employee_name=emp.name,
                leave_type=leave_cat,
                start_date=s_date,
                end_date=e_date,
                days_requested=days,
                reason=reason,
                status="PENDING"
            )
            db.add(new_req)
            db.commit()
            db.refresh(new_req)

            return {
                "success": True,
                "request_id": new_req.id,
                "employee_name": emp.name,
                "leave_type": leave_cat,
                "start_date": str(s_date),
                "end_date": str(e_date),
                "days_requested": days,
                "status": "PENDING",
                "message": f"Leave request #{new_req.id} created successfully for {emp.name} ({days} days)."
            }
        finally:
            db.close()

    @staticmethod
    def approve_leave_request(request_id: int, approver_notes: Optional[str] = None) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
            if not req:
                return {"error": f"Leave request #{request_id} not found"}

            if req.status == "APPROVED":
                return {"warning": f"Leave request #{request_id} is already approved."}

            req.status = "APPROVED"
            req.approver_notes = approver_notes or "Approved automatically via AI Agent HR Governance"

            # Deduct annual leave balance if applicable
            emp = db.query(Employee).filter(Employee.id == req.employee_id).first()
            if emp and req.leave_type == "Annual":
                emp.used_annual_leave = (emp.used_annual_leave or 0) + req.days_requested

            db.commit()
            db.refresh(req)
            return {
                "success": True,
                "request_id": req.id,
                "employee_name": req.employee_name,
                "leave_type": req.leave_type,
                "status": "APPROVED",
                "days": req.days_requested,
                "remaining_annual_leave": emp.remaining_annual_leave if emp else None
            }
        finally:
            db.close()

    @staticmethod
    def reject_leave_request(request_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
            if not req:
                return {"error": f"Leave request #{request_id} not found"}

            req.status = "REJECTED"
            req.approver_notes = reason or "Rejected via AI Agent"
            db.commit()
            db.refresh(req)
            return {
                "success": True,
                "request_id": req.id,
                "employee_name": req.employee_name,
                "status": "REJECTED",
                "reason": req.approver_notes
            }
        finally:
            db.close()

    @staticmethod
    def approve_all_pending_by_department(department: str) -> Dict[str, Any]:
        """Approves all pending leaves for a department (demonstrates batch/parallel action)."""
        db = SessionLocal()
        try:
            pending = (
                db.query(LeaveRequest)
                .join(Employee)
                .filter(LeaveRequest.status == "PENDING", Employee.department.ilike(f"%{department}%"))
                .all()
            )
            if not pending:
                return {"message": f"No pending leave requests found for department: {department}", "count": 0}

            approved_list = []
            for req in pending:
                req.status = "APPROVED"
                req.approver_notes = f"Batch approved for {department} team"
                emp = db.query(Employee).filter(Employee.id == req.employee_id).first()
                if emp and req.leave_type == "Annual":
                    emp.used_annual_leave = (emp.used_annual_leave or 0) + req.days_requested
                approved_list.append({"id": req.id, "employee": req.employee_name, "days": req.days_requested})

            db.commit()
            return {
                "success": True,
                "department": department,
                "approved_count": len(approved_list),
                "approved_requests": approved_list
            }
        finally:
            db.close()
