/* =============================================================================
   Main Entry Point
   Routes to the correct page initializer based on current page
============================================================================= */

(function() {
  "use strict";

  // Detect current page from URL
  function getCurrentPage() {
    const path = window.location.pathname;
    const filename = path.split("/").pop() || "index.html";
    return filename.replace(".html", "") || "index";
  }

  // Page initialization map
  const pageInitializers = {
    "home": () => window.Pages?.home?.init?.(),
    "artists": () => window.Pages?.artists?.init?.(),
    "tour-dates": () => window.Pages?.tourDates?.init?.(),
    "tour-groups": () => window.Pages?.tourGroups?.init?.(),
    "tour-group": () => window.Pages?.tourGroupDetail?.init?.(),
    "optimize": () => window.Pages?.optimize?.init?.(),
    "optimize-detail": () => window.Pages?.optimizeDetail?.init?.(),
    "reports": () => window.Pages?.reports?.init?.(),
    "login": () => window.Pages?.login?.init?.(),
    "signup": () => window.Pages?.signup?.init?.()
  };

  // Initialize the current page
  function init() {
    const page = getCurrentPage();
    const initializer = pageInitializers[page];

    if (initializer) {
      initializer();
    }
  }

  // Run on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
