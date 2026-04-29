requireLogin();
requireRole(["ADMIN"]);

document.getElementById("who").textContent =
  `${localStorage.getItem("name")} (${localStorage.getItem("role")})`;

function toggleManagerField() {
  const role = document.getElementById("userRole").value;
  const managerField = document.getElementById("managerField");
  const managerId = document.getElementById("managerId");

  if (role === "EMPLOYEE") {
    managerField.style.display = "block";
    managerId.required = true;
  } else {
    managerField.style.display = "none";
    managerId.required = false;
    managerId.value = "";
  }
}

async function createUser() {
  const out = document.getElementById("createUserOut");
  out.textContent = "";

  const name = document.getElementById("userName").value.trim();
  const email = document.getElementById("userEmail").value.trim();
  const password = document.getElementById("userPassword").value.trim();
  const role = document.getElementById("userRole").value;
  const managerId = document.getElementById("managerId").value.trim();

  // validation
  if (!name) {
    out.style.color = "red";
    out.textContent = "Name is required.";
    return;
  }

  if (!email) {
    out.style.color = "red";
    out.textContent = "Email is required.";
    return;
  }

  if (!password) {
    out.style.color = "red";
    out.textContent = "Password is required.";
    return;
  }

  if (role === "EMPLOYEE" && !managerId) {
    out.style.color = "red";
    out.textContent = "Manager ID is required for EMPLOYEE.";
    return;
  }

  const params = new URLSearchParams({
    name,
    email,
    password,
    role
  });

  if (role === "EMPLOYEE") {
    params.append("manager_id", managerId);
  }

  try {
    const data = await apiFetch(`/admin/create-user?${params.toString()}`, {
      method: "POST"
    });
    alert("User Created Successfully");
    location.reload();
    //out.style.color = "green";
    //out.textContent = "User created successfully.\n\n" + JSON.stringify(data, null, 2);

    document.getElementById("userName").value = "";
    document.getElementById("userEmail").value = "";
    document.getElementById("userPassword").value = "";
    document.getElementById("userRole").value = "EMPLOYEE";
    document.getElementById("managerId").value = "";

    //toggleManagerField();
  } catch (err) {
    out.style.color = "red";
    out.textContent = "Error: " + err.message;
  }
}

async function createLeaveType() {
  const out = document.getElementById("leaveTypeOut");
  out.textContent = "";

  const name = document.getElementById("leaveTypeName").value.trim();
  const maxPerYear = Number(document.getElementById("leaveTypeAllocation").value);

  if (!name || !maxPerYear) {
    out.style.color = "red";
    out.textContent = "Error: Please enter leave type name and allocation.";
    return;
  }

  // simple code generation from name
  let code = "";
  const words = name.split(/\s+/).filter(Boolean);

  if (words.length >= 2) {
    code = words.map(w => w[0]).join("").toUpperCase();
  } else {
    code = name.slice(0, 2).toUpperCase();
  }

  const params = new URLSearchParams({
    code: code,
    name: name,
    max_per_year: String(maxPerYear)
  });

  try {
    const data = await apiFetch(`/admin/leave-types?${params.toString()}`, {
      method: "POST"
    });
    alert("Leave Type Created Successfully");
    out.style.color = "green";
    out.textContent = "Leave type created successfully.\n\n" + JSON.stringify(data, null, 2);

    document.getElementById("leaveTypeName").value = "";
    document.getElementById("leaveTypeAllocation").value = "";
  } catch (err) {
    out.style.color = "red";
    out.textContent = "Error: " + err.message;
  }
}

async function loadAdminRequests() {
  const box = document.getElementById("requestsOut");
  box.innerHTML = "";

  try {
    const rows = await apiFetch("/admin/requests");

    if (!rows || rows.length === 0) {
      box.innerHTML = `<div class="small">No requests found</div>`;
      return;
    }

    let html = `<table class="table"><thead><tr>
      <th>Request_ID</th><th>Employee ID</th><th>Start</th><th>End</th><th>Status</th><th>Reason</th>
    </tr></thead><tbody>`;

    rows.forEach(r => {
      const st = (r.status || "").toLowerCase();
      html += `<tr>
        <td>${r.request_id ?? r.id ?? "-"}</td>
        <td>${r.employee_name ?? r.employee ?? r.user_name ?? r.employee_id ?? "-"}</td>
        <td>${r.start_date ?? r.start ?? "-"}</td>
        <td>${r.end_date ?? r.end ?? "-"}</td>
        <td><span class="badge ${st}">${r.status ?? "-"}</span></td>
        <td>${r.reason ?? "-"}</td>
      </tr>`;
    });

    html += `</tbody></table>`;
    box.innerHTML = html;
  } catch (err) {
    box.innerHTML = `<div class="small">Error: ${err.message}</div>`;
  }
}

async function loadAudit() {
  const box = document.getElementById("auditOut");
  box.innerHTML = "";

  try {
    const rows = await apiFetch("/admin/audit");

    if (!rows || rows.length === 0) {
      box.innerHTML = `<div class="small">No audit logs found</div>`;
      return;
    }

    let html = `<table class="table"><thead><tr>
      <th>ID</th><th>Action</th><th>User</th><th>Time</th><th>Details</th>
    </tr></thead><tbody>`;

    rows.forEach(r => {
      html += `<tr>
        <td>${r.log_id ?? "-"}</td>
        <td>${r.action ?? "-"}</td>
        <td>${r.actor_id ?? "-"}</td>
        <td>${
          r.timestamp
            ? new Date(r.timestamp).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })
            : "-"
        }</td>
        <td>${r.details ?? "-"}</td>
      </tr>`;
    });

    html += `</tbody></table>`;
    box.innerHTML = html;
  } catch (err) {
    box.innerHTML = `<div class="small">Error: ${err.message}</div>`;
  }
}
//----------------------------------------------------------- 
async function refreshAdminRequestsWithLog() {
  const name = localStorage.getItem("name") || "Unknown User";
  const role = localStorage.getItem("role") || "UNKNOWN";

  try {
    await logUiAction(
      "VIEW_ADMIN_REQUESTS",
      `${role} ${name} clicked Refresh Requests`,
      "LeaveRequest"
    );
  } catch (err) {
    console.error("Audit log failed:", err);
  }

  await loadAdminRequests();
}

async function refreshAuditLogsWithLog() {
  const name = localStorage.getItem("name") || "Unknown User";
  const role = localStorage.getItem("role") || "UNKNOWN";

  try {
    await logUiAction(
      "VIEW_AUDIT_LOGS",
      `${role} ${name} clicked Refresh Audit Logs`,
      "AuditLog"
    );
  } catch (err) {
    console.error("Audit log failed:", err);
  }

  await loadAudit();
}
//=----------------------------------------------------------
window.onload = async function () {
  toggleManagerField();
  await loadAdminRequests();
  await loadAudit();
};