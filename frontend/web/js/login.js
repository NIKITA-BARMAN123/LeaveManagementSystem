async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  const msg = document.getElementById("msg");
  msg.textContent = "";

  try {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);

    const data = await apiFetch("/auth/login", {
      method: "POST",
      isForm: true,
      body: form
    });

    saveAuth(data);

    localStorage.setItem("email", email);

    window.location.href = "dashboard.html";
    
  } catch (err) {
    msg.style.color = "red";
    msg.textContent = "Login failed: email and password are required";
  }
}