import json
from typing import List, Dict, Any, Optional
from backend.config import POLICIES_JSON_PATH


class JSONKnowledgeSource:
    """Retrieves and queries company policies stored in JSON format."""

    def __init__(self):
        self.source_name = "JSON Knowledge Base (Company Policies)"
        self._load_policies()

    def _load_policies(self):
        try:
            with open(POLICIES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.policies = data.get("policies", [])
        except Exception as e:
            print(f"[JSONKnowledgeSource] Error loading policies: {e}")
            self.policies = []

    def get_all_policies(self) -> List[Dict[str, Any]]:
        return self.policies

    def search_policies(self, query: str = "", category: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        q_lower = query.lower().strip()
        cat_lower = category.lower().strip() if category else None

        for policy in self.policies:
            if cat_lower and policy.get("category", "").lower() != cat_lower:
                continue

            if not q_lower:
                results.append(policy)
                continue

            title = policy.get("title", "").lower()
            content = policy.get("content", "").lower()
            pid = policy.get("id", "").lower()

            if q_lower in title or q_lower in content or q_lower in pid:
                results.append(policy)

        return results

    def get_policy_by_id(self, policy_id: str) -> Optional[Dict[str, Any]]:
        for policy in self.policies:
            if policy.get("id", "").upper() == policy_id.strip().upper():
                return policy
        return None
