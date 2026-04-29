requireLogin();
requireRole(["MANAGER"]);

document.getElementById("who").textContent =
  `${localStorage.getItem("name")} (${localStorage.getItem("role")})`;

function getRequestId(r) {
  return r.request_id ?? r.id ?? "";
}

function getEmployeeName(r) {
  return r.employee_name ?? r.employee ?? r.user_name ?? "-";
}

function getStatusClass(status) {
  return (status || "").toLowerCase();
}

async function loadPendingRequests() {
  const box = document.getElementById("pendingRequestsOut");
  box.innerHTML = "";

  try {
    const rows = await apiFetch("/manager/requests");

    const pendingRows = (rows || []).filter(r =>
      (r.status || "").toUpperCase() === "PENDING"
    );

    if (pendingRows.length === 0) {
      box.innerHTML = `<div class="small">No pending requests found</div>`;
      return;
    }

    let html = `
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Employee</th>
            <th>Start</th>
            <th>End</th>
            <th>Status</th>
            <th>Reason</th>
            <th>Decision</th>
            <th>Comment</th>
            <th>Finalize</th>
          </tr>
        </thead>
        <tbody>
    `;

    pendingRows.forEach(r => {
      const requestId = getRequestId(r);
      const status = r.status ?? "-";
      const st = getStatusClass(status);

      html += `
        <tr>
          <td>${requestId}</td>
          <td>${getEmployeeName(r)}</td>
          <td>${r.start_date ?? "-"}</td>
          <td>${r.end_date ?? "-"}</td>
          <td><span class="badge ${st}">${status}</span></td>
          <td>${r.reason ?? "-"}</td>
          <td>
            <select id="decisionAction_${requestId}">
              <option value="">Select</option>
              <option value="APPROVED">APPROVED</option>
              <option value="REJECTED">REJECTED</option>
            </select>
          </td>
          <td>
            <textarea
              id="decisionComment_${requestId}"
              rows="2"
              placeholder="Enter comment"
              style="min-width:180px;"
            ></textarea>
          </td>
          <td style="text-align:center;">
            <button
              title="Finalize"
              onclick="submitDecisionForRow(${requestId})"
              style="padding:6px 10px; cursor:pointer;"
            >
              ✔
            </button>
          </td>
        </tr>
      `;
    });

    html += `</tbody></table>`;
    box.innerHTML = html;
  } catch (err) {
    box.innerHTML = `<div class="small">Error: ${err.message}</div>`;
  }
}

async function loadHistoryRequests() {
  const box = document.getElementById("historyRequestsOut");
  box.innerHTML = "";

  try {
    const rows = await apiFetch("/manager/requests");

    const historyRows = (rows || []).filter(r => {
      const s = (r.status || "").toUpperCase();
      return s === "APPROVED" || s === "REJECTED";
    });

    if (historyRows.length === 0) {
      box.innerHTML = `<div class="small">No approved/rejected history found</div>`;
      return;
    }

    let html = `
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Employee</th>
            <th>Start</th>
            <th>End</th>
            <th>Status</th>
            <th>Reason</th>
            <th>Comment</th>
          </tr>
        </thead>
        <tbody>
    `;

    historyRows.forEach(r => {
      const status = r.status ?? "-";
      const st = getStatusClass(status);

      html += `
        <tr>
          <td>${getRequestId(r)}</td>
          <td>${getEmployeeName(r)}</td>
          <td>${r.start_date ?? "-"}</td>
          <td>${r.end_date ?? "-"}</td>
          <td><span class="badge ${st}">${status}</span></td>
          <td>${r.reason ?? "-"}</td>
          <td>${r.comment ?? r.manager_comment ?? "-"}</td>
        </tr>
      `;
    });

    html += `</tbody></table>`;
    box.innerHTML = html;
  } catch (err) {
    box.innerHTML = `<div class="small">Error: ${err.message}</div>`;
  }
}
//------------------------------------------------------------------
async function refreshPendingRequestsWithLog() {
  const name = localStorage.getItem("name") || "Unknown User";
  const role = localStorage.getItem("role") || "UNKNOWN";

  try {
    await logUiAction(
      "VIEW_PENDING_REQUESTS",
      `${role} ${name} clicked Refresh Pending Requests`,
      "LeaveRequest"
    );
  } catch (err) {
    console.error("Audit log failed:", err);
  }

  await loadPendingRequests();
  await loadPendingBadge();
}

async function refreshHistoryRequestsWithLog() {
  const name = localStorage.getItem("name") || "Unknown User";
  const role = localStorage.getItem("role") || "UNKNOWN";

  try {
    await logUiAction(
      "VIEW_MANAGER_HISTORY",
      `${role} ${name} clicked Refresh History`,
      "LeaveRequest"
    );
  } catch (err) {
    console.error("Audit log failed:", err);
  }

  await loadHistoryRequests();
}
//-----------------------------------------------------------------------
async function submitDecisionForRow(requestId) {
  const actionValue = document.getElementById(`decisionAction_${requestId}`).value;
  const commentValue = document.getElementById(`decisionComment_${requestId}`).value.trim();

  if (!actionValue) {
    alert("Please select APPROVED or REJECTED first.");
    return;
  }

  const action = actionValue === "APPROVED" ? "APPROVE" : "REJECT";

  try {
    await apiFetch(
      `/manager/decide?request_id=${requestId}&action=${encodeURIComponent(action)}&comment=${encodeURIComponent(commentValue)}`,
      { method: "POST" }
    );

    alert("Decision submitted successfully.");

    await loadPendingRequests();
    await loadHistoryRequests();
    await loadPendingBadge();

  } catch (err) {
    alert("Error: " + err.message);
  }
}

async function loadPendingBadge() {
  const badge = document.getElementById("pendingBadge");
  if (!badge) return;

  try {
    const rows = await apiFetch("/manager/requests");

    const pendingRows = (rows || []).filter(r =>
      (r.status || "").toUpperCase() === "PENDING"
    );

    const count = pendingRows.length;

    if (count > 0) {
      badge.textContent = count;
      badge.style.display = "inline-flex";
    } else {
      badge.style.display = "none";
    }
  } catch (err) {
    console.error("Failed to load pending badge:", err);
    badge.style.display = "none";
  }
}

window.onload = async function () {
  await loadPendingRequests();
  await loadHistoryRequests();
  await loadPendingBadge();
};