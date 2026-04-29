function saveAuth({ access_token, role, name, user_id }) {
  localStorage.setItem("token", access_token);
  localStorage.setItem("role", role);
  localStorage.setItem("name", name || "");
  localStorage.setItem("user_id", user_id || "");
}

async function logout() {
  const token = localStorage.getItem("token");

  try {
    if (token) {
      await fetch(`${window.CONFIG.API_BASE}/auth/logout`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
    }
  } catch (err) {
    console.error("Logout API failed:", err);
  }

  localStorage.removeItem("token");
  localStorage.removeItem("role");
  localStorage.removeItem("name");
  localStorage.removeItem("user_id")

  //window.location.href = "login.html";

  console.warn("Redirect blocked for debugging");
  window.location.href = "login.html";
}

function requireLogin() {
  const token = localStorage.getItem("token");
  if (!token) {
    console.warn("No token found");
    window.location.href = "login.html";
  }
}

function requireRole(roles = []) {
  const role = localStorage.getItem("role");
  if (!roles.includes(role)) {
    console.warn("Role not allowed:", role);
    return;
  }
}