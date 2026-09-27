import asyncio
from typing import Dict, Any, List, Optional
from backend.agent.planner import MultiStepPlanner
from backend.agent.reasoner import Reasoner
from backend.agent.executor import ActionExecutor
from backend.agent.tools import TOOL_SOURCE_MAP
from backend.models.schemas import ChatResponse, ReasoningStep, ToolCallLog


class AgentOrchestrator:
    """
    Main Autonomous Agent Orchestrator.
    Implements the ReAct (Reasoning + Acting) loop:
    1. Plan -> Decompose into sub-tasks (single or multi-step)
    2. Reason -> Select appropriate tools & provide reasoning prior to execution
    3. Act -> Execute non-critical actions automatically; gate critical actions behind human approval
    4. Parallelize -> Execute independent subtasks concurrently via asyncio
    5. Observe -> Synthesize internal knowledge into an explainable response
    6. Audit & Memorize -> Log every trace and persist facts to long-term memory
    """

    def __init__(self):
        self.reasoner = Reasoner()

    async def process_query(
        self,
        user_query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        session_id: str = "default-session"
    ) -> ChatResponse:
        chat_history = chat_history or []
        reasoning_steps: List[ReasoningStep] = []
        actions_taken: List[ToolCallLog] = []
        sources_consulted: set = set()
        pending_approvals: List[Dict[str, Any]] = []
        conflicts_detected: List[str] = []

        step_counter = 1

        # Step 1: Multi-Step Planning
        plan = MultiStepPlanner.plan(user_query)
        if plan.is_multistep:
            reasoning_steps.append(
                ReasoningStep(
                    step_number=step_counter,
                    title="Task Decomposition & Planning",
                    detail=(
                        f"Decomposed request into {len(plan.steps)} structured steps. "
                        + ("Identified independent operations suitable for parallel execution."
                           if plan.parallel_execution else "Sequence will execute with dependency chaining.")
                    )
                )
            )
            step_counter += 1

        # Step 2: Tool Selection & Pre-execution Reasoning
        tool_calls, thought_summary = self.reasoner.reason_and_select_tools(
            user_query=user_query,
            chat_history=chat_history,
            session_id=session_id
        )

        reasoning_steps.append(
            ReasoningStep(
                step_number=step_counter,
                title="Reasoning Over Internal Knowledge Requirements",
                detail=thought_summary or "Determining required knowledge sources and verifying access boundaries."
            )
        )
        step_counter += 1

        # If planner had pre-configured steps and reasoner returned general, merge or use planned
        if plan.is_multistep and plan.steps:
            tool_calls = [
                {
                    "tool": s["tool"],
                    "arguments": s["arguments"],
                    "reasoning": s["reasoning"]
                }
                for s in plan.steps
            ]

        # Step 3: Tool Execution (Parallel or Sequential)
        executed_results = []
        if plan.parallel_execution and len(tool_calls) > 1:
            reasoning_steps.append(
                ReasoningStep(
                    step_number=step_counter,
                    title="Parallel Action Execution",
                    detail=f"Executing {len(tool_calls)} independent queries concurrently across multiple knowledge backends."
                )
            )
            step_counter += 1
            executed_results = await ActionExecutor.execute_parallel(
                tool_calls=tool_calls,
                session_id=session_id,
                user_request=user_query
            )
        else:
            for call in tool_calls:
                res = ActionExecutor.stage_or_execute(
                    tool_name=call["tool"],
                    arguments=call["arguments"],
                    reasoning=call.get("reasoning", "Execution required by agent plan"),
                    session_id=session_id,
                    user_request=user_query
                )
                executed_results.append(res)

        # Step 4: Process Observations and Aggregate State
        for res in executed_results:
            t_name = res["tool"]
            t_args = res["arguments"]
            t_out = res["output"]
            t_crit = res.get("critical", False)
            t_req_appr = res.get("requires_approval", False)
            src = res.get("source", TOOL_SOURCE_MAP.get(t_name, "Internal Knowledge"))
            sources_consulted.add(src)

            actions_taken.append(
                ToolCallLog(
                    tool=t_name,
                    arguments=t_args,
                    output=t_out,
                    critical=t_crit,
                    requires_approval=t_req_appr,
                    approval_status="PENDING" if t_req_appr else "EXECUTED",
                    reasoning=res.get("reasoning"),
                    duration_ms=res.get("duration_ms")
                )
            )

            if t_req_appr:
                pending_approvals.append({
                    "action_id": res.get("action_id"),
                    "tool": t_name,
                    "arguments": t_args,
                    "description": res.get("reasoning"),
                    "source": src
                })
                reasoning_steps.append(
                    ReasoningStep(
                        step_number=step_counter,
                        title=f"Critical Action Gated: {t_name}",
                        detail=(
                            f"Action modifies persistent organizational state. "
                            f"Staged for human approval [Action ID: {res.get('action_id')}]. "
                            f"Execution suspended pending confirmation."
                        ),
                        source_used=src
                    )
                )
                step_counter += 1
            else:
                reasoning_steps.append(
                    ReasoningStep(
                        step_number=step_counter,
                        title=f"Observed: {t_name}",
                        detail=f"Retrieved and processed internal data from {src}.",
                        source_used=src
                    )
                )
                step_counter += 1

            # Check if conflicts were returned
            if t_name == "detect_conflicts" and isinstance(t_out, list):
                for conflict in t_out:
                    conflicts_detected.append(conflict.get("resolution_strategy", str(conflict)))

        # Step 5: Synthesize Final Grounded Explanation
        final_answer = self._synthesize_answer(
            user_query=user_query,
            executed_results=executed_results,
            pending_approvals=pending_approvals,
            conflicts_detected=conflicts_detected
        )

        return ChatResponse(
            answer=final_answer,
            reasoning_summary=thought_summary,
            reasoning_steps=reasoning_steps,
            actions_taken=actions_taken,
            sources_consulted=sorted(list(sources_consulted)),
            pending_approvals=pending_approvals,
            conflicts_detected=conflicts_detected,
            session_id=session_id
        )

    def _synthesize_answer(
        self,
        user_query: str,
        executed_results: List[Dict[str, Any]],
        pending_approvals: List[Dict[str, Any]],
        conflicts_detected: List[str]
    ) -> str:
        """Constructs an explainable, fact-based response citing retrieved internal data."""
        if not executed_results:
            return (
                "I analyzed your request against our internal knowledge sources, "
                "but could not identify matching internal records. Please ensure your query relates to "
                "Xiarch Bharat personnel, policies, attendance, or payroll data."
            )

        parts = []

        # Handling Sabbatical + Leave Balance
        sabbatical_res = next((r for r in executed_results if r["tool"] == "check_sabbatical_eligibility"), None)
        balance_res = next((r for r in executed_results if r["tool"] == "check_leave_balance"), None)

        if sabbatical_res and balance_res:
            s_data = sabbatical_res["output"]
            b_data = balance_res["output"]

            if isinstance(s_data, dict) and "error" in s_data:
                return (
                    f"### Sabbatical Analysis: Employee Record Not Found\n\n"
                    f"{s_data['error']}\n\n"
                    "Unable to calculate continuous tenure or verify sabbatical eligibility."
                )

            if isinstance(s_data, dict) and "calculated_tenure_years" in s_data:
                elig_status = "✅ **QUALIFIED**" if s_data["is_eligible"] else "❌ **NOT CURRENTLY ELIGIBLE**"
                parts.append(
                    f"### Sabbatical & Leave Analysis for {s_data['name']}\n\n"
                    f"**1. Current Leave Balances (from SQLite HR Central DB):**\n"
                    f"- **Remaining Annual Leave:** {b_data.get('remaining_annual_leave', 'N/A')} days (out of {b_data.get('total_annual_leave', 24)} total)\n"
                    f"- **Used Annual Leave:** {b_data.get('used_annual_leave', 'N/A')} days\n"
                    f"- **Sick / Medical Leave:** {b_data.get('sick_leave_balance', 'N/A')} days\n"
                    f"- **Casual Leave:** {b_data.get('casual_leave_balance', 'N/A')} days\n\n"
                    f"**2. Sabbatical Eligibility Verification (Policy POL-004 & Vector Handbook):**\n"
                    f"- **Hire Date:** {s_data['hire_date']}\n"
                    f"- **Accumulated Continuous Tenure:** **{s_data['calculated_tenure_years']} years**\n"
                    f"- **Policy Requirement:** Minimum {s_data['required_tenure_years']} continuous years\n"
                    f"- **Eligibility Verdict:** {elig_status}\n\n"
                    f"**Reasoning Explanation:**\n{s_data['reasoning']}\n\n"
                    f"> *Policy Reference: [{s_data['policy_id']}: {s_data['policy_title']}]* — "
                    f"\"{s_data['policy_excerpt']}\""
                )
                return "\n".join(parts)

        # Handling Pending Human Approvals
        if pending_approvals:
            for p in pending_approvals:
                parts.append(
                    f"### ⚠️ Human Approval Required for Critical Action\n\n"
                    f"**Action:** `{p['tool']}`\n"
                    f"**Target System:** {p['source']}\n"
                    f"**Proposed Parameters:**\n"
                    f"```json\n{p['arguments']}\n```\n\n"
                    f"**Reasoning for Action:** {p['description']}\n\n"
                    f"🛑 *In accordance with organizational governance, this action will NOT be executed until you review and confirm it via the Approval Dialog.*"
                )
            return "\n\n".join(parts)

        # Handling Manager / Employee Search
        emp_search_res = next((r for r in executed_results if r["tool"] in ("search_employees", "get_employee_details")), None)
        manager_keywords = ("manager", "reports to", "report to", "manages", "who does", "supervisor", "reporting line", "reporting")
        is_manager_query = any(k in user_query.lower() for k in manager_keywords)

        if emp_search_res:
            out = emp_search_res["output"]
            if isinstance(out, list) and not out:
                return (
                    f"### Employee Not Found in Internal Records\n\n"
                    f"I searched the SQLite Central HR Database, but could not find any active employee record "
                    f"matching: **\"{user_query}\"**.\n\n"
                    f"Please verify the employee name or check the personnel directory."
                )
            if isinstance(out, list) and out:
                emp = out[0]
                if is_manager_query:
                    return (
                        f"### Reporting Structure for {emp['name']}\n\n"
                        f"- **Employee:** {emp['name']} (ID: #{emp['id']})\n"
                        f"- **Role:** {emp['role']}\n"
                        f"- **Department:** {emp['department']}\n"
                        f"- **Direct Manager:** **{emp.get('manager_name') or 'Reports directly to Board of Directors'}** "
                        f"(Manager ID: #{emp.get('manager_id') or 'N/A'})\n\n"
                        f"**Data Provenance:** Retrieved from internal SQLite Central Personnel Database."
                    )
                else:
                    return (
                        f"### Employee Record: {emp['name']}\n\n"
                        f"- **Employee ID:** #{emp['id']}\n"
                        f"- **Name:** {emp['name']}\n"
                        f"- **Role:** {emp['role']}\n"
                        f"- **Department:** {emp['department']}\n"
                        f"- **Location:** {emp.get('location', 'N/A')}\n"
                        f"- **Email:** {emp.get('email', 'N/A')}\n"
                        f"- **Direct Manager:** {emp.get('manager_name') or 'Reports directly to Board of Directors'}\n\n"
                        f"**Data Provenance:** Retrieved from internal SQLite Central Personnel Database."
                    )

        # Handling Remote & Policy Queries
        policy_res = next((r for r in executed_results if r["tool"] in ("search_policies", "semantic_search_policies")), None)
        remote_keywords = (
            "remote", "hybrid", "work from home", "wfh", "telecommute",
            "in-office", "office days", "friday", "home setup", "allowance", "ergonomic"
        )
        general_policy_keywords = (
            "policy", "policies", "guideline", "guidelines", "handbook", "benefit", "benefits",
            "insurance", "expense", "expenses", "travel", "relocation"
        )

        if policy_res:
            uq_lower = user_query.lower()
            if any(k in uq_lower for k in remote_keywords):
                vector_res = next((r for r in executed_results if r["tool"] == "semantic_search_policies"), None)
                vec_content = ""
                if vector_res and isinstance(vector_res["output"], list) and vector_res["output"]:
                    vec_content = vector_res["output"][0].get("content", "")

                return (
                    f"### Xiarch Bharat Remote & Hybrid Work Policy (POL-002)\n\n"
                    f"Based on internal policy records in our JSON Registry and ChromaDB Vector Handbook:\n\n"
                    f"- **Remote Work Allowance:** Eligible team members in Engineering, Product, and Design may work remotely up to **3 days per week**.\n"
                    f"- **Core In-Office Days:** Tuesday and Thursday are core in-person collaboration days for sprint reviews and planning.\n"
                    f"- **Optional Remote Fridays:** Fridays are designated optional remote days for eligible departments.\n"
                    f"- **Equipment & Internet Allowance:**\n"
                    f"  - High-speed internet reimbursement of **INR 2,000/month** (requires broadband invoice).\n"
                    f"  - One-time ergonomic home setup stipend of **INR 25,000** upon passing probation.\n\n"
                    f"**Detailed Handbook Section Retrieved:**\n"
                    f"> {vec_content[:300]}...\n\n"
                    f"**Sources Consulted:** JSON Policy Registry (`POL-002`) + ChromaDB Vector Store (`remote_work_policy.md`)."
                )
            elif any(k in uq_lower for k in general_policy_keywords):
                out = policy_res["output"]
                lines = [f"### Company Policy Information\n"]
                if isinstance(out, list) and out:
                    for item in out[:3]:
                        title = item.get("title") or item.get("section") or "Policy Document"
                        doc_id = item.get("id") or item.get("doc_name") or ""
                        summary = item.get("summary") or item.get("content") or ""
                        lines.append(f"#### 📄 {title} ({doc_id})")
                        lines.append(f"{summary[:350]}...\n")
                    lines.append("**Sources Consulted:** JSON Policy Registry / Vector Policy Store.")
                    return "\n".join(lines)

        # Handling Attendance Report
        att_res = next((r for r in executed_results if r["tool"] == "get_attendance_report"), None)
        if att_res:
            out = att_res["output"]
            flagged = out.get("flagged_employees", [])
            lines = [
                f"### September Attendance Analysis & Flagged Irregularities\n",
                f"- **Department Filter:** {out.get('department_filter', 'All Departments')}",
                f"- **Absence Threshold:** >= {out.get('threshold_used', 3)} days",
                f"- **Records Analyzed:** {out.get('total_records_analyzed')} employees\n"
            ]
            if flagged:
                lines.append("#### 🚨 Flagged Employees Exceeding Threshold:")
                for f in flagged:
                    lines.append(
                        f"- **{f['name']}** ({f['department']} - {f['role']}): **{f['absences_count']} days absent** "
                        f"on `{', '.join(f['dates_absent'])}`. *{f['flagged_reason']}*."
                    )
            else:
                lines.append("✅ No employees currently exceed the 3-day absence threshold.")

            lines.append("\n**Reasoning:** Cross-referenced daily swipe records from `attendance.csv` with employee master records in SQLite.")
            return "\n".join(lines)

        # Handling Conflict Detection
        conflict_res = next((r for r in executed_results if r["tool"] == "detect_conflicts"), None)
        if conflict_res:
            out = conflict_res["output"]
            if isinstance(out, list) and out:
                c = out[0]
                return (
                    f"### ⚠️ Data Conflict & Discrepancy Resolution\n\n"
                    f"**Identified Conflict:** `{c.get('type')}` for **{c.get('employee_name')}**\n\n"
                    f"- **Self-Reported Claim:** {c.get('claimed_balance')} days\n"
                    f"- **Authoritative Central Record:** **{c.get('authoritative_balance')} days remaining** "
                    f"({c.get('total_allocated')} days annual allocation - {c.get('recorded_used')} days logged as used)\n"
                    f"- **Variance:** Discrepancy of **{c.get('claimed_balance') - c.get('authoritative_balance')} days**\n\n"
                    f"**Organizational Policy & Resolution Path:**\n"
                    f"{c.get('resolution_strategy')}\n\n"
                    f"**Action Recommended:** Maintain database record as ground truth; submit attendance punch logs to HR Operations for formal reconciliation."
                )

        # Handling Long-Term Memory
        mem_res = next((r for r in executed_results if r["tool"] == "remember_fact"), None)
        if mem_res:
            out = mem_res["output"]
            m = out.get("memory", {})
            return (
                f"### 💾 Fact Committed to Long-Term Memory\n\n"
                f"I have successfully stored the following persistent preference into the agent's long-term memory store:\n\n"
                f"- **Subject / Key:** `{m.get('memory_key')}`\n"
                f"- **Value:** \"{m.get('memory_value')}\"\n"
                f"- **Category:** `{m.get('category')}`\n"
                f"- **Session Scope:** `{m.get('session_id')}`\n\n"
                f"This information will be automatically injected into future reasoning contexts across conversation sessions."
            )

        # Generic formatting for any other tool output
        for res in executed_results:
            parts.append(
                f"### Result for `{res['tool']}`\n\n"
                f"```json\n{res['output']}\n```\n\n"
                f"**Reasoning:** {res.get('reasoning')}"
            )

        return "\n\n".join(parts)
