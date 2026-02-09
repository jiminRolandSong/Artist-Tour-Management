/* =============================================================================
   Shared UI Components
   Toast notifications, loaders, sidebar, etc.
============================================================================= */

// -----------------------------------------------------------------------------
// Toast Notifications
// -----------------------------------------------------------------------------
const ToastManager = {
  container: null,

  init() {
    if (this.container) return;
    this.container = document.createElement("div");
    this.container.className = "toast-container";
    document.body.appendChild(this.container);
  },

  show(message, type = "success", duration = 4000) {
    this.init();

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div class="toast-content">
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close" aria-label="Close">&times;</button>
    `;

    this.container.appendChild(toast);

    const closeBtn = toast.querySelector(".toast-close");
    closeBtn.addEventListener("click", () => this.remove(toast));

    if (duration > 0) {
      setTimeout(() => this.remove(toast), duration);
    }

    return toast;
  },

  remove(toast) {
    toast.style.animation = "slideIn 0.3s ease reverse";
    setTimeout(() => toast.remove(), 300);
  },

  success(message, duration) {
    return this.show(message, "success", duration);
  },

  error(message, duration) {
    return this.show(message, "error", duration);
  },

  warning(message, duration) {
    return this.show(message, "warning", duration);
  }
};

// -----------------------------------------------------------------------------
// Loading States
// -----------------------------------------------------------------------------
function showLoader(element) {
  if (!element) return;
  element.classList.add("loading");
  const overlay = document.createElement("div");
  overlay.className = "loading-overlay";
  overlay.innerHTML = '<div class="spinner"></div>';
  element.style.position = "relative";
  element.appendChild(overlay);
}

function hideLoader(element) {
  if (!element) return;
  element.classList.remove("loading");
  const overlay = element.querySelector(".loading-overlay");
  if (overlay) overlay.remove();
}

function setButtonLoading(button, loading = true) {
  if (!button) return;
  if (loading) {
    button.disabled = true;
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = '<div class="spinner spinner-sm"></div>';
  } else {
    button.disabled = false;
    button.innerHTML = button.dataset.originalText || button.innerHTML;
  }
}

// -----------------------------------------------------------------------------
// Sidebar Management
// -----------------------------------------------------------------------------
const Sidebar = {
  init() {
    this.sidebar = document.querySelector(".sidebar");
    this.overlay = document.querySelector(".sidebar-overlay");
    this.menuBtn = document.querySelector(".mobile-menu-btn");

    if (this.menuBtn) {
      this.menuBtn.addEventListener("click", () => this.toggle());
    }

    if (this.overlay) {
      this.overlay.addEventListener("click", () => this.close());
    }

    // Set active link
    this.setActiveLink();
  },

  toggle() {
    if (!this.sidebar) return;
    this.sidebar.classList.toggle("open");
    this.overlay?.classList.toggle("visible");
    this.menuBtn?.classList.toggle("active");
  },

  close() {
    if (!this.sidebar) return;
    this.sidebar.classList.remove("open");
    this.overlay?.classList.remove("visible");
    this.menuBtn?.classList.remove("active");
  },

  setActiveLink() {
    const currentPage = window.location.pathname.split("/").pop() || "home.html";
    const links = document.querySelectorAll(".sidebar-link");

    links.forEach(link => {
      const href = link.getAttribute("href");
      if (href === currentPage) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });
  }
};

// -----------------------------------------------------------------------------
// Date Utilities
// -----------------------------------------------------------------------------
function parseISODate(value) {
  if (!value) return null;
  return new Date(`${value}T00:00:00`);
}

function getToday() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function formatDate(date) {
  if (!date) return "";
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric"
  });
}

function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

// -----------------------------------------------------------------------------
// Form Utilities
// -----------------------------------------------------------------------------
function getFormData(form) {
  const formData = new FormData(form);
  const data = {};
  for (const [key, value] of formData.entries()) {
    data[key] = value;
  }
  return data;
}

function clearForm(form) {
  if (form) form.reset();
}

function setMinDate(input, daysFromNow = 1) {
  if (!input) return;
  const today = getToday();
  const minDate = new Date(today.getTime() + daysFromNow * 24 * 60 * 60 * 1000);
  input.min = minDate.toISOString().split("T")[0];
}

// -----------------------------------------------------------------------------
// Page Initialization
// -----------------------------------------------------------------------------
function initPage(options = {}) {
  const { requireAuth: needsAuth = true, onLoad } = options;

  // Check auth
  if (needsAuth && !window.API.requireAuth()) {
    return;
  }

  // Init sidebar
  Sidebar.init();

  // Bind logout
  const logoutBtn = document.getElementById("logout");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => window.API.logout());
  }

  // Run page-specific init
  if (onLoad) {
    onLoad();
  }
}

// Export
window.UI = {
  Toast: ToastManager,
  Sidebar,
  showLoader,
  hideLoader,
  setButtonLoading,
  parseISODate,
  getToday,
  formatDate,
  getQueryParam,
  getFormData,
  clearForm,
  setMinDate,
  initPage
};
