function getToken() {
  return localStorage.getItem("token");
}

async function apiFetch(path, { method = "GET", headers = {}, body = null, isForm = false } = {}) {
  const url = `${window.CONFIG.API_BASE}${path}`;

  const finalHeaders = { ...headers };

  const token = getToken();
  if (token) finalHeaders["Authorization"] = `Bearer ${token}`;

  if (isForm) {
    finalHeaders["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body && !(body instanceof FormData)) {
    finalHeaders["Content-Type"] = "application/json";
  }

  const res = await fetch(url, {
    method,
    headers: finalHeaders,
    body
  });

  let data = null;
  const text = await res.text();
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!res.ok) {
    console.error("API ERROR STATUS:", res.status);
    console.error("API RESPONSE:", data);

    let msg = `Request failed (${res.status})`;

    if (data && data.detail) {
      if (Array.isArray(data.detail)) {
        msg = data.detail
          .map(item => `${item.loc?.join(" > ") || "field"}: ${item.msg}`)
          .join("\n");
      } else if (typeof data.detail === "string") {
        msg = data.detail;
      } else {
        msg = JSON.stringify(data.detail, null, 2);
      }
    }

    throw new Error(msg);
  }

  return data;
}
async function logUiAction(action, details = "", targetType = "UI", targetId = "") {
  const qs = new URLSearchParams({
    action,
    target_type: targetType,
    details
  });

  if (targetId !== "" && targetId !== null && targetId !== undefined) {
    qs.append("target_id", targetId);
  }

  await apiFetch(`/audit/log?${qs.toString()}`, { method: "POST" });
}