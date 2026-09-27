from typing import List, Dict, Any, Optional
from backend.knowledge.loader import knowledge_manager


class PolicyService:
    @staticmethod
    def search_policies(query: str = "", category: Optional[str] = None) -> List[Dict[str, Any]]:
        return knowledge_manager.json_policies.search_policies(query, category)

    @staticmethod
    def semantic_policy_search(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        try:
            results = knowledge_manager.vector_store.search_documents(query, top_k=top_k)
            if results:
                return results
        except Exception as e:
            print(f"[PolicyService] Vector search error: {e}. Falling back to JSON policies.")

        # Degradation to JSON-policy-only
        try:
            json_res = knowledge_manager.json_policies.search_policies(query=query)
            if json_res:
                return [
                    {
                        "doc_name": f"{p.get('id', 'POL')}.json",
                        "section": p.get("title", "Policy Document"),
                        "content": f"[{p.get('id')} - {p.get('title')}]\n{p.get('summary', '')}\n{p.get('details', '')}",
                        "similarity_score": 1.0
                    }
                    for p in json_res[:top_k]
                ]
        except Exception as err:
            print(f"[PolicyService] JSON policy fallback error: {err}")

        return []

    @staticmethod
    def check_sabbatical_eligibility(employee_name_or_id: str) -> Dict[str, Any]:
        """
        Multi-source reasoning check:
        Combines SQLite (employee tenure & department) with JSON/Vector Policy POL-004
        """
        import datetime
        from backend.knowledge.loader import knowledge_manager

        emp = None
        if str(employee_name_or_id).strip().isdigit():
            emp = knowledge_manager.sqlite.get_employee_by_id(int(employee_name_or_id))
        else:
            emp = knowledge_manager.sqlite.get_employee_by_name(employee_name_or_id)

        if not emp:
            return {"error": f"Employee '{employee_name_or_id}' not found in HR records."}

        # Calculate tenure
        hire_date_str = emp["hire_date"]
        hire_date = datetime.date.fromisoformat(hire_date_str)
        today = datetime.date(2026, 9, 26)  # current system time context
        tenure_days = (today - hire_date).days
        tenure_years = round(tenure_days / 365.25, 1)

        # Policy requirement is 5 continuous years
        policy = knowledge_manager.json_policies.get_policy_by_id("POL-004")
        policy_docs = knowledge_manager.vector_store.search_documents("sabbatical eligibility tenure criteria", top_k=1)

        eligible = tenure_years >= 5.0
        return {
            "employee_id": emp["id"],
            "name": emp["name"],
            "role": emp["role"],
            "department": emp["department"],
            "hire_date": hire_date_str,
            "calculated_tenure_years": tenure_years,
            "required_tenure_years": 5.0,
            "is_eligible": eligible,
            "policy_id": "POL-004",
            "policy_title": "Sabbatical & Long Leave Policy",
            "policy_excerpt": (
                "Employees with a minimum of 5 continuous years of tenure are eligible to apply for "
                "an unpaid or partially sponsored sabbatical leave of up to 3 months."
            ),
            "reasoning": (
                f"{emp['name']} joined on {hire_date_str} and has accumulated {tenure_years} years of service. "
                + (f"This satisfies the 5-year threshold required by POL-004. Sabbatical eligibility is CONFIRMED."
                   if eligible else
                   f"This is below the 5-year threshold required by POL-004. Short by {round(5.0 - tenure_years, 1)} years.")
            )
        }
