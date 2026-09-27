document.addEventListener("DOMContentLoaded", () => {
  const chatForm = document.getElementById("chatForm");
  const queryInput = document.getElementById("queryInput");
  const messagesViewport = document.getElementById("messagesViewport");
  const submitBtn = document.getElementById("submitBtn");

  // Drawers
  const auditDrawer = document.getElementById("auditDrawer");
  const memoryDrawer = document.getElementById("memoryDrawer");
  const drawerBackdrop = document.getElementById("drawerBackdrop");
  const btnOpenAudit = document.getElementById("btnOpenAudit");
  const btnOpenMemory = document.getElementById("btnOpenMemory");
  const btnCloseAudit = document.getElementById("btnCloseAudit");
  const btnCloseMemory = document.getElementById("btnCloseMemory");
  const auditLogsContainer = document.getElementById("auditLogsContainer");
  const memoryContainer = document.getElementById("memoryContainer");

  // Modal
  const approvalModal = document.getElementById("approvalModal");
  const approvalModalBody = document.getElementById("approvalModalBody");
  const btnApproveAction = document.getElementById("btnApproveAction");
  const btnRejectAction = document.getElementById("btnRejectAction");
  let activePendingAction = null;

  const sessionId = "xiarch-session-" + Math.random().toString(36).substring(2, 9);

  // Auto-resize textarea
  queryInput.addEventListener("input", () => {
    queryInput.style.height = "auto";
    queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + "px";
  });

  // Scenario Pills
  document.querySelectorAll(".scenario-pill").forEach(pill => {
    pill.addEventListener("click", () => {
      const prompt = pill.getAttribute("data-prompt");
      queryInput.value = prompt;
      queryInput.dispatchEvent(new Event("input"));
      chatForm.dispatchEvent(new Event("submit"));
    });
  });

  // Drawer Controls
  btnOpenAudit.addEventListener("click", () => {
    openDrawer(auditDrawer);
    loadAuditLogs();
  });

  btnOpenMemory.addEventListener("click", () => {
    openDrawer(memoryDrawer);
    loadMemories();
  });

  btnCloseAudit.addEventListener("click", () => closeDrawers());
  btnCloseMemory.addEventListener("click", () => closeDrawers());
  drawerBackdrop.addEventListener("click", () => closeDrawers());

  function openDrawer(drawer) {
    drawer.classList.add("open");
    drawerBackdrop.classList.add("open");
  }

  function closeDrawers() {
    auditDrawer.classList.remove("open");
    memoryDrawer.classList.remove("open");
    drawerBackdrop.classList.remove("open");
  }

  // Submit Chat Form
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;

    // Append user message
    appendUserMessage(query);
    queryInput.value = "";
    queryInput.style.height = "auto";
    submitBtn.disabled = true;

    // Loading indicator
    const loadingElem = appendLoadingMessage();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: query,
          session_id: sessionId
        })
      });

      const data = await res.json();
      loadingElem.remove();

      if (res.ok) {
        appendAssistantMessage(data);

        // Check if any critical action is waiting for approval
        if (data.pending_approvals && data.pending_approvals.length > 0) {
          triggerApprovalModal(data.pending_approvals[0]);
        }
      } else {
        appendErrorMessage(data.detail || "Server returned an unexpected error.");
      }
    } catch (err) {
      loadingElem.remove();
      appendErrorMessage("Network error: Could not reach agent server.");
      console.error(err);
    } finally {
      submitBtn.disabled = false;
      queryInput.focus();
    }
  });

  // UI Appenders
  function appendUserMessage(text) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const row = document.createElement("div");
    row.className = "message-row user";
    row.innerHTML = `
      <div class="avatar user-avatar">YOU</div>
      <div class="message-bubble">
        <div class="message-header">
          <span class="sender-name">Operator</span>
          <span class="timestamp">${time}</span>
        </div>
        <div class="message-body">${escapeHtml(text)}</div>
      </div>
    `;
    messagesViewport.appendChild(row);
    scrollToBottom();
  }

  function appendLoadingMessage() {
    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.innerHTML = `
      <div class="avatar ai-avatar">AI</div>
      <div class="message-bubble">
        <div class="message-body" style="color: #818cf8; display: flex; align-items: center; gap: 0.5rem;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
            <line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line>
            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
            <line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line>
            <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
          </svg>
          Reasoning over internal knowledge sources...
        </div>
      </div>
    `;
    messagesViewport.appendChild(row);
    scrollToBottom();
    return row;
  }

  function appendAssistantMessage(data) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const row = document.createElement("div");
    row.className = "message-row assistant";

    // Format reasoning accordion
    let reasoningHtml = "";
    if (data.reasoning_steps && data.reasoning_steps.length > 0) {
      const stepsHtml = data.reasoning_steps.map(s => `
        <div class="reasoning-step">
          <div class="step-num">${s.step_number}</div>
          <div class="step-info">
            <div class="step-title">${escapeHtml(s.title)}</div>
            <div class="step-detail">${escapeHtml(s.detail)}</div>
          </div>
        </div>
      `).join("");

      reasoningHtml = `
        <div class="reasoning-accordion">
          <button class="reasoning-trigger" type="button">
            <span>🧠 Agent Reasoning Trace (${data.reasoning_steps.length} steps)</span>
            <span class="chevron">▼</span>
          </button>
          <div class="reasoning-content open">
            ${stepsHtml}
          </div>
        </div>
      `;
    }

    // Format metadata chips
    const sourcesHtml = (data.sources_consulted || []).map(src => `<span class="meta-chip">📚 ${escapeHtml(src)}</span>`).join("");
    const actionsHtml = (data.actions_taken || []).map(a => {
      const isCrit = a.critical ? "meta-chip-critical" : "";
      const dur = a.duration_ms ? ` (${a.duration_ms}ms)` : "";
      return `<span class="meta-chip ${isCrit}">⚡ ${escapeHtml(a.tool)}${dur}</span>`;
    }).join("");

    row.innerHTML = `
      <div class="avatar ai-avatar">AI</div>
      <div class="message-bubble">
        <div class="message-header">
          <span class="sender-name">Xiarch Bharat Autonomous Agent</span>
          <span class="timestamp">${time}</span>
        </div>
        ${reasoningHtml}
        <div class="message-body">${formatMarkdown(data.answer)}</div>
        <div class="meta-chips-bar">
          ${sourcesHtml}
          ${actionsHtml}
        </div>
      </div>
    `;

    messagesViewport.appendChild(row);

    // Setup accordion click
    const trigger = row.querySelector(".reasoning-trigger");
    if (trigger) {
      trigger.addEventListener("click", () => {
        const content = trigger.nextElementSibling;
        const open = content.classList.toggle("open");
        trigger.querySelector(".chevron").textContent = open ? "▼" : "▶";
      });
    }

    scrollToBottom();
  }

  function appendErrorMessage(err) {
    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.innerHTML = `
      <div class="avatar ai-avatar">!</div>
      <div class="message-bubble" style="border-color: rgba(244,63,94,0.4)">
        <div class="message-body" style="color: #fda4af;">
          ⚠️ <strong>Execution Error:</strong> ${escapeHtml(err)}
        </div>
      </div>
    `;
    messagesViewport.appendChild(row);
    scrollToBottom();
  }

  // Approval Modal Handlers
  function triggerApprovalModal(pendingItem) {
    activePendingAction = pendingItem;
    approvalModalBody.innerHTML = `
      <p style="margin-bottom: 0.75rem;">The AI agent proposed the following <strong>state-modifying action</strong>:</p>
      <div style="margin-bottom: 0.5rem;"><strong>Action:</strong> <code style="color:#38bdf8;">${escapeHtml(pendingItem.tool)}</code></div>
      <div style="margin-bottom: 0.5rem;"><strong>Target:</strong> ${escapeHtml(pendingItem.source || 'SQLite Central DB')}</div>
      <div style="margin-bottom: 0.5rem;"><strong>Parameters:</strong></div>
      <pre style="margin-bottom: 0.75rem;">${escapeHtml(JSON.stringify(pendingItem.arguments, null, 2))}</pre>
      <div style="color: #fbbf24;"><strong>Reasoning:</strong> ${escapeHtml(pendingItem.description || '')}</div>
    `;
    approvalModal.classList.add("open");
  }

  btnApproveAction.addEventListener("click", async () => {
    if (!activePendingAction) return;
    try {
      const res = await fetch("/api/approval", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action_id: activePendingAction.action_id,
          approved: true,
          reason: "Approved by Human Operator via UI Modal"
        })
      });
      const data = await res.json();
      approvalModal.classList.remove("open");

      appendConfirmationMessage(
        `✅ <strong>Action Approved & Executed:</strong> <code>${activePendingAction.tool}</code> executed successfully. ` +
        `Result: <pre>${JSON.stringify(data.output, null, 2)}</pre>`
      );
    } catch (e) {
      alert("Error approving action: " + e);
    }
  });

  btnRejectAction.addEventListener("click", async () => {
    if (!activePendingAction) return;
    try {
      await fetch("/api/approval", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action_id: activePendingAction.action_id,
          approved: false,
          reason: "Rejected by Human Operator"
        })
      });
      approvalModal.classList.remove("open");
      appendConfirmationMessage(`🛑 <strong>Action Cancelled:</strong> <code>${activePendingAction.tool}</code> was cancelled by human operator.`);
    } catch (e) {
      alert("Error rejecting action: " + e);
    }
  });

  function appendConfirmationMessage(html) {
    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.innerHTML = `
      <div class="avatar ai-avatar">AI</div>
      <div class="message-bubble" style="border-color: rgba(16, 185, 129, 0.4)">
        <div class="message-body">${html}</div>
      </div>
    `;
    messagesViewport.appendChild(row);
    scrollToBottom();
  }

  // Load Audit Logs
  async function loadAuditLogs() {
    auditLogsContainer.innerHTML = '<div class="loading-spinner">Fetching audit records...</div>';
    try {
      const res = await fetch("/api/audit-logs?limit=50");
      const data = await res.json();
      if (!data.logs || data.logs.length === 0) {
        auditLogsContainer.innerHTML = '<div style="color: #64748b; font-size: 0.8rem;">No audit records found yet.</div>';
        return;
      }

      auditLogsContainer.innerHTML = data.logs.map(log => {
        const statusClass = log.status === "SUCCESS" ? "status-success" : (log.status === "PENDING_APPROVAL" ? "status-pending" : "status-failed");
        return `
          <div class="audit-card">
            <div class="audit-meta">
              <span>${log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}</span>
              <span class="audit-status ${statusClass}">${log.status}</span>
            </div>
            <div class="audit-tool">${escapeHtml(log.tool_name)}</div>
            <div style="color: #94a3b8; font-size: 0.72rem; margin: 4px 0;">Reason: ${escapeHtml(log.reasoning || 'N/A')}</div>
            <details style="margin-top: 4px;">
              <summary style="font-size: 0.68rem; color: #64748b; cursor: pointer;">View Payload</summary>
              <pre style="font-size: 0.65rem; margin-top: 4px;">In: ${escapeHtml(log.tool_input)}\nOut: ${escapeHtml(log.tool_output)}</pre>
            </details>
          </div>
        `;
      }).join("");
    } catch (e) {
      auditLogsContainer.innerHTML = '<div style="color: #fda4af;">Failed to load audit logs.</div>';
    }
  }

  // Load Memories
  async function loadMemories() {
    memoryContainer.innerHTML = '<div class="loading-spinner">Fetching persistent memories...</div>';
    try {
      const res = await fetch("/api/memories");
      const data = await res.json();
      if (!data.memories || data.memories.length === 0) {
        memoryContainer.innerHTML = '<div style="color: #64748b; font-size: 0.8rem;">Memory vault is empty. Tell the agent "Remember that..." to persist facts.</div>';
        return;
      }

      memoryContainer.innerHTML = data.memories.map(m => `
        <div class="audit-card" style="border-left: 3px solid #818cf8;">
          <div class="audit-meta">
            <span style="color: #a5b4fc; font-weight: 600;">${escapeHtml(m.category.toUpperCase())}</span>
            <span>${m.updated_at ? new Date(m.updated_at).toLocaleDateString() : ''}</span>
          </div>
          <div style="font-weight: 600; color: #e2e8f0; margin-bottom: 3px;">${escapeHtml(m.memory_key)}</div>
          <div style="color: #94a3b8; font-size: 0.75rem;">"${escapeHtml(m.memory_value)}"</div>
        </div>
      `).join("");
    } catch (e) {
      memoryContainer.innerHTML = '<div style="color: #fda4af;">Failed to load memories.</div>';
    }
  }

  function scrollToBottom() {
    messagesViewport.scrollTop = messagesViewport.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMarkdown(text) {
    if (!text) return "";
    // Basic markdown formatting
    let html = escapeHtml(text);
    // Code blocks
    html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Blockquote
    html = html.replace(/^&gt; (.*$)/gim, '<blockquote>$1</blockquote>');
    // Unordered lists
    html = html.replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    // Paragraph breaks
    html = html.replace(/\n\n+/g, '<br><br>');
    return html;
  }
});
