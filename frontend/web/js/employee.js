requireLogin();
requireRole(["EMPLOYEE"]);

document.getElementById("who").textContent =
  `${localStorage.getItem("name")} (${localStorage.getItem("role")})`;

async function sendChat(e) {

  console.log("sendChat triggered");

  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }  

  const inputBox = document.getElementById("chatMsg");
  const message = inputBox.value.trim();
  const out = document.getElementById("chatOut");

  if (!message) return;

  try {
    const data = await apiFetch(`/chat?message=${encodeURIComponent(message)}`, {
      method: "POST"
    });

    // always show user message
    out.innerHTML += `
      <div style="color: #fff; text-align: right; margin-top:10px;">
        You: ${message}
      </div>
    `;

    //if final submission → show alert instead of chat
    if (data.intent === "APPLY_LEAVE" && data.data && data.data.request_id) {
      alert(data.reply);

      location.reload();
    } else {
      // normal bot response
      out.innerHTML = `
        <div style="color: #00cfff; text-align: center;">
          ${data.reply}
        </div>
        <div style="color: #888; font-size: 12px;">
          (intent: ${data.intent})
        </div>
      `;
    }

    // ✅ AUTO SCROLL
    out.scrollTop = out.scrollHeight;

    // ❗ DO NOT CLEAR INPUT (as per your requirement)
    inputBox.focus();

    if (data.intent === "APPLY_LEAVE" && data.data && data.data.request_id) {
      alert(data.reply);
      await loadHistory();
      await loadBalance();
    }

  } catch (err) {
      console.error("CHAT ERROR:", err);
      out.innerHTML += `<div style="color:red;">Error: ${err.message}</div>`;
    }
}

async function loadBalance() {
  const box = document.getElementById("balanceOut");
  box.innerHTML = "";

  try {
    const rows = await apiFetch("/employee/balance");
    if (!rows || rows.length === 0) {
      box.innerHTML = `<div class="small">No data</div>`;
      return;
    }

    // rows might be objects; show simple table
    let html = `<table class="table"><thead><tr>
      <th>Leave Type</th><th>Total</th><th>Used</th><th>Remaining</th>
    </tr></thead><tbody>`;

    rows.forEach(r => {
      html += `<tr>
        <td>${r.leave_type || r.leave_type_name || r.type || r.leave_type_id || "-"}</td>
        <td>${r.total_allocated ?? r.total ?? r.allocated ?? "-"}</td>
        <td>${r.used ?? "-"}</td>
        <td>${r.remaining ?? "-"}</td>
      </tr>`;
    });

    html += `</tbody></table>`;
    box.innerHTML = html;
  } catch (err) {
    box.innerHTML = `<div class="small">Error: ${err.message}</div>`;
  }
}

async function loadHistory() {
  const box = document.getElementById("historyOut");
  box.innerHTML = "";

  try {
    const rows = await apiFetch("/employee/history");
    if (!rows || rows.length === 0) {
      box.innerHTML = `<div class="small">No history</div>`;
      return;
    }

    let html = `<table class="table"><thead><tr>
      <th>ID</th><th>Start</th><th>End</th><th>Days</th><th>Status</th>
    </tr></thead><tbody>`;

    rows.forEach(r => {
      const st = (r.status || "").toLowerCase();
      html += `<tr>
        <td>${r.request_id ?? "-"}</td>
        <td>${r.start_date ?? r.start ?? "-"}</td>
        <td>${r.end_date ?? r.end ?? "-"}</td>
        <td>${r.days_count ?? r.days ?? "-"}</td>
        <td><span class="badge ${st}">${r.status}</span></td>
      </tr>`;
    });

    html += `</tbody></table>`;
    box.innerHTML = html;
  } catch (err) {
    box.innerHTML = `<div class="small">Error: ${err.message}</div>`;
  }
}

//--------------------------------------------------
async function refreshBalanceWithLog() {
  const name = localStorage.getItem("name") || "Unknown User";
  const role = localStorage.getItem("role") || "UNKNOWN";

  try {
    await logUiAction(
      "VIEW_BALANCE_PAGE",
      `${role} ${name} clicked Refresh Balance`,
      "LeaveBalance"
    );
  } catch (err) {
    console.error("Audit log failed:", err);
  }

  await loadBalance();
}

async function refreshHistoryWithLog() {
  const name = localStorage.getItem("name") || "Unknown User";
  const role = localStorage.getItem("role") || "UNKNOWN";

  try {
    await logUiAction(
      "VIEW_EMPLOYEE_HISTORY_PAGE",
      `${role} ${name} clicked Refresh History`,
      "LeaveRequest"
    );
  } catch (err) {
    console.error("Audit log failed:", err);
  }

  await loadHistory();
}
//--------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("sendBtn");

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    sendChat(e);   // ✅ pass event
  });

  document.getElementById("chatMsg").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendChat(e);
    }
  });
});