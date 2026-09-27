from typing import Dict, Any, List, Optional
from backend.knowledge.loader import knowledge_manager


class AttendanceService:
    @staticmethod
    def get_attendance_report(department: Optional[str] = None, absence_threshold: int = 3) -> Dict[str, Any]:
        """
        Retrieves attendance CSV data and correlates with employee directory to flag high absenteeism.
        Requirement: 'Show me attendance report and flag anyone with >3 absences'
        """
        raw_report = knowledge_manager.csv_logs.get_absenteeism_report()
        flagged_raw = raw_report["flagged_employees_high_absences"]

        detailed_flags = []
        for item in flagged_raw:
            emp = knowledge_manager.sqlite.get_employee_by_id(item["employee_id"])
            if emp:
                if department and department.lower() not in emp["department"].lower():
                    continue
                detailed_flags.append({
                    "employee_id": emp["id"],
                    "name": emp["name"],
                    "department": emp["department"],
                    "role": emp["role"],
                    "absences_count": item["absences"],
                    "dates_absent": item["dates_absent"],
                    "flagged_reason": f"Exceeded absenteeism threshold ({item['absences']} >= {absence_threshold} days)",
                    "requires_hr_review": True
                })

        return {
            "total_records_analyzed": len(raw_report["all_summary"]),
            "threshold_used": absence_threshold,
            "department_filter": department or "All Departments",
            "flagged_employees": detailed_flags,
            "full_summary": raw_report["all_summary"]
        }

    @staticmethod
    def get_payroll_summary(department: Optional[str] = None) -> Dict[str, Any]:
        return knowledge_manager.csv_logs.get_department_payroll_summary(department)
