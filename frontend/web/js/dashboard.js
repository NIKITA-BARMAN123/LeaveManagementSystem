requireLogin();

const role = localStorage.getItem("role");
const name = localStorage.getItem("name") || "User";

document.getElementById("who").textContent = `${name}`;
document.getElementById("roleLabel").textContent = role || "-";
document.getElementById("emailLabel").textContent = localStorage.getItem("email");

const dashboardOptions = document.getElementById("dashboardOptions");
const dashboardTitle = document.getElementById("dashboardTitle");
const dashboardSubtitle = document.getElementById("dashboardSubtitle");

function goToRoleHome() {
  if (role === "ADMIN") {
    window.location.href = "admin.html";
  } else if (role === "MANAGER") {
    window.location.href = "manager.html";
  } else if (role === "EMPLOYEE") {
    window.location.href = "employee.html#full-panel";
  } else {
    alert("Invalid role. Please login again.");
    logout();
  }
}

function openOption(page, sectionId = "") {
  if (sectionId) {
    window.location.href = `${page}#${sectionId}`;
  } else {
    window.location.href = page;
  }
}
//dashboardOptions
function createOptionCard(
  title,
  description,
  page,
  sectionId = "",
  shouldLog = false,
  action = "",
  targetType = "UI",
  detailText = "",
  iconClass = "fa-solid fa-circle"   // 🔥 NEW
) 
{
  const card = document.createElement("div");
  card.className = "option-card";

  card.innerHTML = `
    <div class="dashboard-card-head">
      <div class="card-title-row">
        <i class="${iconClass} card-icon"></i>
        <h3>${title}</h3>
      </div>
      <span class="notif-badge dashboard-badge" style="display:none;">0</span>
    </div>
    <p>${description}</p>
  `;

  card.onclick = async () => {
    const name = localStorage.getItem("name") || "Unknown User";
    const userId = localStorage.getItem("user_id") || "Unknown ID";

    try {
      if (shouldLog && action) {
        await logUiAction(
          action,
          `${userId}, ${name} ${detailText}`,
          targetType
        );
      }
    } catch (err) {
      console.error("Audit log failed:", err);
    }

    openOption(page, sectionId);
  };

  return card;
}
async function updatePendingBadgeOnDashboard() {
  if (role !== "MANAGER") return;

  try {
    const rows = await apiFetch("/manager/requests");

    const pendingRows = (rows || []).filter(r =>
      (r.status || "").toUpperCase() === "PENDING"
    );

    const count = pendingRows.length;

    // find the "View Pending Request" card
    const cards = document.querySelectorAll(".option-card");

    cards.forEach(card => {
      const title = card.querySelector("h3")?.textContent;

      if (title === "View Pending Request") {
        const badge = card.querySelector(".dashboard-badge");

        if (count > 0) {
          badge.textContent = count;
          badge.style.display = "inline-flex";
        } else {
          badge.style.display = "none";
        }
      }
    });

  } catch (err) {
    console.error("Dashboard badge error:", err);
  }
}
function renderDashboard() {
  dashboardOptions.innerHTML = "";

  if (role === "ADMIN") {
    dashboardTitle.textContent = "Admin";
    dashboardSubtitle.textContent = "Choose an action.";

    dashboardOptions.appendChild(
      createOptionCard(
        "Create User",
        "Add a new employee, manager, or admin user.",
        "admin.html",
        "create-user",
        false,
        "", "", "",
        "fa-solid fa-user-plus"
      )
    );

    dashboardOptions.appendChild(
      createOptionCard(
        "Create Leave Type",
        "Add a new leave type and set yearly allocation.",
        "admin.html",
        "create-leave-type",
        false,
        "", "", "",
        "fa-solid fa-calendar-plus"
      )
    );

    dashboardOptions.appendChild(
      createOptionCard(
        "View Leave Status",
        "Check all submitted leave requests.",
        "admin.html",
        "all-request",
        true,
        "VIEW_LEAVE_STATUS",
        "LeaveStatus",
        "checked employees' leave status",
        "fa-solid fa-list-check"
      )
    );

    dashboardOptions.appendChild(
      createOptionCard(
        "View Audit Logs",
        "See system actions and activity logs.",
        "admin.html",
        "audit-logs",
        true,
        "VIEW_AUDIT_LOGS",
        "AuditLogs",
        "checked Audit logs",
        "fa-solid fa-file-lines"
      )
    );
  }
  else if (role === "MANAGER") {
    dashboardTitle.textContent = "Manager Dashboard";
    dashboardSubtitle.textContent = "Choose a manager action.";

    dashboardOptions.appendChild(
      createOptionCard(
        "View Pending Request",
        "See only pending leave requests and take action on them.",
        "manager.html",
        "pending-requests",
        true,
        "VIEW_PENDING_REQUEST",
        "PendingRequest",
        "checked pending requests",
        "fa-solid fa-clock"
      )
    );

    dashboardOptions.appendChild(
      createOptionCard(
        "View Approved / Rejected History",
        "See only approved and rejected leave requests.",
        "manager.html",
        "history-requests",
        true,
        "VIEW_APPROVED_OR_REJECTED_HISTORY",
        "ApproveRejectRequest",
        "checked approved/rejected requests",
        "fa-solid fa-check-double"
      )
    );
  }
  else if (role === "EMPLOYEE") {
    dashboardTitle.textContent = "Employee Dashboard";
    dashboardSubtitle.textContent = "Choose an employee action.";

  
    dashboardOptions.appendChild(
      createOptionCard(
        "Apply Leave",
        "Submit a leave request using chat.",
        "employee.html",
        "apply-leave",
        false,
        "", "", "",
        "fa-solid fa-paper-plane"
      )
    );

    dashboardOptions.appendChild(
      createOptionCard(
        "Check Leave Balance",
        "See your available leave balance.",
        "employee.html",
        "leave-balance",
        true,
        "VIEW_BALANCE_PAGE",
        "LeaveBalance",
        "checked their leave",
        "fa-solid fa-wallet"
      )
    );

    dashboardOptions.appendChild(
      createOptionCard(
        "View Leave History",
        "See your previous leave requests.",
        "employee.html",
        "leave-history",
        true,
        "VIEW_EMPLOYEE_HISTORY_PAGE",
        "LeaveRequest",
        "checked their leave history",
        "fa-solid fa-clock-rotate-left"
      )
    );
  }
  else {
    alert("Invalid role. Please login again.");
    logout();
  }
}

renderDashboard();
updatePendingBadgeOnDashboard();
// goToRoleHome