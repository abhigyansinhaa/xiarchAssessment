import csv
from typing import List, Dict, Any, Optional
from backend.config import ATTENDANCE_CSV_PATH, PAYROLL_CSV_PATH


class CSVKnowledgeSource:
    """Retrieves and queries attendance and payroll records from CSV data files."""

    def __init__(self):
        self.source_name = "CSV Knowledge Base (Attendance & Payroll Logs)"

    def get_attendance_by_employee(self, employee_id: int) -> List[Dict[str, Any]]:
        results = []
        try:
            with open(ATTENDANCE_CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if int(row["employee_id"]) == int(employee_id):
                        results.append(row)
        except Exception as e:
            print(f"[CSVKnowledgeSource] Error reading attendance: {e}")
        return results

    def get_all_attendance(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        try:
            with open(ATTENDANCE_CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if status_filter:
                        if row.get("status", "").lower() == status_filter.lower():
                            results.append(row)
                    else:
                        results.append(row)
        except Exception as e:
            print(f"[CSVKnowledgeSource] Error reading all attendance: {e}")
        return results

    def get_absenteeism_report(self) -> Dict[str, Any]:
        """Summarizes absenteeism counts across employees."""
        records = self.get_all_attendance()
        summary: Dict[int, Dict[str, Any]] = {}
        for r in records:
            eid = int(r["employee_id"])
            if eid not in summary:
                summary[eid] = {"employee_id": eid, "total_records": 0, "absences": 0, "lates": 0, "dates_absent": []}
            summary[eid]["total_records"] += 1
            if r["status"] == "absent":
                summary[eid]["absences"] += 1
                summary[eid]["dates_absent"].append(r["date"])
            elif r["status"] == "late":
                summary[eid]["lates"] += 1

        flagged = [v for v in summary.values() if v["absences"] >= 3]
        return {
            "flagged_employees_high_absences": flagged,
            "all_summary": list(summary.values())
        }

    def get_payroll_by_employee(self, employee_id: int) -> Optional[Dict[str, Any]]:
        try:
            with open(PAYROLL_CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if int(row["employee_id"]) == int(employee_id):
                        return row
        except Exception as e:
            print(f"[CSVKnowledgeSource] Error reading payroll: {e}")
        return None

    def get_department_payroll_summary(self, department: Optional[str] = None) -> Dict[str, Any]:
        records = []
        try:
            with open(PAYROLL_CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if department:
                        if row["department"].lower() == department.lower():
                            records.append(row)
                    else:
                        records.append(row)

            total_payout = sum(float(r["net_salary_inr"]) for r in records)
            return {
                "department": department or "All Departments",
                "employee_count": len(records),
                "total_net_payout_inr": total_payout,
                "records": records
            }
        except Exception as e:
            print(f"[CSVKnowledgeSource] Error calculating payroll summary: {e}")
            return {"error": str(e)}
