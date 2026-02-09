/* =============================================================================
   Home Page Logic
============================================================================= */

async function loadHomeSummary() {
  const upcomingList = document.getElementById("upcoming-tour-list");
  const summaryEl = document.getElementById("upcoming-summary");
  const insightsEl = document.getElementById("tour-insights");

  if (!upcomingList || !summaryEl) return;

  try {
    const tourDates = await window.API.request("/api/tours/");
    const today = window.UI.getToday();

    const upcoming = tourDates
      .filter(t => window.UI.parseISODate(t.date) >= today)
      .sort((a, b) => window.UI.parseISODate(a.date) - window.UI.parseISODate(b.date));

    summaryEl.textContent = `${upcoming.length} upcoming dates`;

    upcomingList.innerHTML = upcoming.length
      ? upcoming.slice(0, 10).map(t =>
          `<li class="list-item">
            <span><strong>${t.artist.name}</strong> @ ${t.venue.name}</span>
            <span class="muted">${t.date}</span>
          </li>`
        ).join("")
      : '<li class="muted">No upcoming tours.</li>';

    // Render insights
    if (insightsEl) {
      renderInsights(tourDates, insightsEl);
    }

    // Render map
    const mapInstance = window.MapManager?.create("tour-map");
    if (mapInstance) {
      mapInstance.renderTours(tourDates);
    }
  } catch (err) {
    summaryEl.textContent = "Failed to load tours.";
    upcomingList.innerHTML = `<li class="text-error">${err.message}</li>`;
    window.UI.Toast.error(err.message);
  }
}

function renderInsights(tours, container) {
  if (!tours.length) {
    container.textContent = "No tours yet. Create your first tour to see insights.";
    return;
  }

  const today = window.UI.getToday();
  const upcoming = tours.filter(t => window.UI.parseISODate(t.date) >= today);
  const past = tours.filter(t => window.UI.parseISODate(t.date) < today);
  const nextTour = upcoming.sort((a, b) =>
    window.UI.parseISODate(a.date) - window.UI.parseISODate(b.date)
  )[0];
  const avgPrice = tours.reduce((sum, t) => sum + Number(t.ticket_price || 0), 0) / tours.length;

  container.innerHTML = `
    <div class="content-grid-2" style="gap: var(--space-md);">
      <div>
        <div class="muted">Total tours</div>
        <div style="font-size: 1.5rem; font-weight: 600;">${tours.length}</div>
      </div>
      <div>
        <div class="muted">Upcoming / Past</div>
        <div style="font-size: 1.5rem; font-weight: 600;">${upcoming.length} / ${past.length}</div>
      </div>
      <div>
        <div class="muted">Next tour</div>
        <div style="font-size: 1.1rem; font-weight: 600;">${nextTour ? nextTour.date : "N/A"}</div>
      </div>
      <div>
        <div class="muted">Avg ticket price</div>
        <div style="font-size: 1.1rem; font-weight: 600;">$${avgPrice.toFixed(2)}</div>
      </div>
    </div>
  `;
}

// Initialize
function initHomePage() {
  window.UI.initPage({
    onLoad: loadHomeSummary
  });
}

window.Pages = window.Pages || {};
window.Pages.home = { init: initHomePage };
