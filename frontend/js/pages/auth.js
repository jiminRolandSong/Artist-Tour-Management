/* =============================================================================
   Auth Pages Logic (Login & Signup)
============================================================================= */

function bindLoginForm() {
  const form = document.querySelector("form");
  const errorEl = document.querySelector(".login-error");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    if (!username || !password) {
      if (errorEl) errorEl.textContent = "Username and password are required.";
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    window.UI.setButtonLoading(submitBtn, true);

    try {
      await window.API.login(username, password);
      window.location.href = "home.html";
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
    } finally {
      window.UI.setButtonLoading(submitBtn, false);
    }
  });
}

function bindSignupForm() {
  const form = document.querySelector("form");
  const errorEl = document.querySelector(".signup-error");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";

    const username = document.getElementById("username").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirm = document.getElementById("confirm").value;

    if (!username || !email || !password) {
      if (errorEl) errorEl.textContent = "Username, email, and password are required.";
      return;
    }

    if (password !== confirm) {
      if (errorEl) errorEl.textContent = "Passwords do not match.";
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    window.UI.setButtonLoading(submitBtn, true);

    try {
      await window.API.register(username, email, password);
      window.location.href = "home.html";
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
    } finally {
      window.UI.setButtonLoading(submitBtn, false);
    }
  });
}

// Initialize
function initLoginPage() {
  bindLoginForm();
}

function initSignupPage() {
  bindSignupForm();
}

window.Pages = window.Pages || {};
window.Pages.login = { init: initLoginPage };
window.Pages.signup = { init: initSignupPage };
