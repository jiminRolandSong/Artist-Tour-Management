/* =============================================================================
   API Client & Authentication
============================================================================= */

const API_BASE = "http://127.0.0.1:8000";

// Token management
function saveToken(token) {
  localStorage.setItem("access_token", token);
}

function getToken() {
  return localStorage.getItem("access_token");
}

function clearToken() {
  localStorage.removeItem("access_token");
}

function isAuthenticated() {
  return !!getToken();
}

// API request wrapper
async function apiRequest(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    let message = "Request failed";
    if (error && typeof error === "string") {
      message = error;
    } else if (error && typeof error === "object") {
      if (error.detail) {
        message = error.detail;
      } else {
        const firstKey = Object.keys(error)[0];
        if (firstKey) {
          const value = error[firstKey];
          message = Array.isArray(value) ? value[0] : String(value);
        }
      }
    }
    throw new Error(message);
  }

  if (res.status === 204) {
    return null;
  }
  const text = await res.text();
  if (!text) {
    return null;
  }
  return JSON.parse(text);
}

// Auth functions
async function login(username, password) {
  const res = await fetch(`${API_BASE}/api/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password })
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Login failed");
  }

  const data = await res.json();
  if (!data.access) {
    throw new Error("No access token returned");
  }

  saveToken(data.access);
  return data;
}

async function register(username, email, password) {
  const res = await fetch(`${API_BASE}/api/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password })
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    const detail = (error.username && error.username[0]) || (error.email && error.email[0]) || error.detail;
    throw new Error(detail || "Registration failed");
  }

  return res.json();
}

function logout() {
  clearToken();
  window.location.href = "login.html";
}

function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}

// Export
window.API = {
  request: apiRequest,
  login,
  register,
  logout,
  requireAuth,
  isAuthenticated,
  getToken
};
