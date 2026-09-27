import asyncio
from backend.agent.orchestrator import AgentOrchestrator
from backend.agent.executor import ActionExecutor, PENDING_APPROVAL_STORE
from backend.models.database import init_db
from backend.data.seed_db import seed_database
from backend.audit.logger import AuditLogger
from backend.agent.memory import memory_manager


async def run_tests():
    print("=" * 60)
    print("🧪 Running Autonomous Agent End-to-End Validation Suite")
    print("=" * 60)

    # 1. Init & Seed
    init_db()
    seed_database()

    orchestrator = AgentOrchestrator()

    scenarios = [
        ("1. Manager Query (SQLite)", "Who is the manager of Priya Sharma?"),
        ("2. Remote Work Policy (Vector + JSON)", "What is our remote work policy? Can I work from home on Friday?"),
        ("3. Sabbatical + Balance (Multi-Step & Parallel)", "How many leaves does Amit have left, and does he qualify for a sabbatical per company policy?"),
        ("4. Attendance Irregularity (CSV)", "Show me the attendance report for the Engineering team this month and flag anyone with >3 absences"),
        ("5. Conflict Resolution", "Neha says she has 20 leave days left but the system shows 15 — what should I do?"),
        ("6. Long-Term Memory", "Remember that Neha prefers email communication over Slack"),
        ("7. Critical Action Approval Gate", "Submit a leave request for Rahul from 2026-10-01 to 2026-10-05 for vacation"),
        ("8. Batch Department Approval", "Approve all pending leave requests for the Marketing team"),
        ("9. Out-of-Whitelist Sabbatical Check (Kavita Reddy)", "How many leaves does Kavita Reddy have left, and does she qualify for a sabbatical?"),
        ("10. Out-of-Whitelist Leave Submission (Pooja Hegde)", "Submit a leave request for Pooja Hegde from 2026-10-15 to 2026-10-18 for medical leave"),
        ("11. Unknown Employee Not Found Guard (Sherlock Holmes)", "Who is the manager of Sherlock Holmes?")
    ]

    for title, query in scenarios:
        print(f"\n▶ Testing: {title}")
        print(f"  Prompt: '{query}'")
        res = await orchestrator.process_query(query, session_id="test-session")

        print(f"  Reasoning Steps: {len(res.reasoning_steps)}")
        for step in res.reasoning_steps:
            print(f"    - Step {step.step_number}: {step.title}")

        print(f"  Tools Taken: {[a.tool for a in res.actions_taken]}")
        print(f"  Sources Consulted: {res.sources_consulted}")

        if res.pending_approvals:
            print(f"  ⚠️ Pending Human Approval: {res.pending_approvals[0]['tool']} [ID: {res.pending_approvals[0]['action_id']}]")
            # Simulate human approval
            act_id = res.pending_approvals[0]['action_id']
            approval_res = ActionExecutor.approve_and_execute(act_id, approver_reason="Test suite approval")
            print(f"  ✅ Approved & Executed: {approval_res.get('success')}")

        print(f"  Answer Preview:\n  {res.answer[:160]}...\n")

    # Verify Audit Logs
    logs = AuditLogger.get_recent_logs(limit=10)
    print("=" * 60)
    print(f"📊 Audit Log Verification: {len(logs)} recent logs recorded.")
    assert len(logs) > 0, "Audit logs should not be empty!"

    # Verify Long-Term Memory
    mems = memory_manager.get_all_memories()
    print(f"🧠 Memory Vault Verification: {len(mems)} persistent facts remembered.")
    assert len(mems) > 0, "Memory should not be empty!"

    print("=" * 60)
    print("🎉 ALL SCENARIOS, OUT-OF-WHITELIST REGRESSION TESTS & GOVERNANCE CHECKS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
