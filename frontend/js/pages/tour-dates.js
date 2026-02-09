/* =============================================================================
   Tour Dates Page Logic
============================================================================= */

async function loadTourDatesPage() {
  const tourList = document.getElementById("tour-list");
  const pastTourList = document.getElementById("past-tour-list");
  const archivedTourList = document.getElementById("archived-tour-list");
  const venueSelect = document.getElementById("tour-venue");
  const artistSelect = document.getElementById("tour-artist");
  const tourGroupSelect = document.getElementById("tour-group");

  if (!tourList) return;

  window.UI.showLoader(tourList.parentElement);

  try {
    const [tourDates, venues, artists, tourGroups] = await Promise.all([
      window.API.request("/api/tours/"),
      window.API.request("/api/venues/"),
      window.API.request("/api/artists/"),
      window.API.request("/api/tour-groups/")
    ]);

    const today = window.UI.getToday();
    const activeTours = tourDates.filter(t => !t.is_archived);
    const upcomingTours = activeTours.filter(t => window.UI.parseISODate(t.date) >= today);
    const pastTours = activeTours.filter(t => window.UI.parseISODate(t.date) < today);
    const archivedTours = tourDates.filter(t => t.is_archived);

    // Render upcoming
    tourList.innerHTML = upcomingTours.length
      ? upcomingTours.map(t => renderTourItem(t, ["archive", "delete"])).join("")
      : '<li class="muted">No upcoming tours.</li>';

    // Render past
    if (pastTourList) {
      pastTourList.innerHTML = pastTours.length
        ? pastTours.map(t => renderTourItem(t, ["archive", "delete"])).join("")
        : '<li class="muted">No past tours.</li>';
    }

    // Render archived
    if (archivedTourList) {
      archivedTourList.innerHTML = archivedTours.length
        ? archivedTours.map(t => renderTourItem(t, ["restore", "delete"])).join("")
        : '<li class="muted">No archived tours.</li>';
    }

    // Populate selects
    if (artistSelect) {
      artistSelect.innerHTML = artists.map(a => `<option value="${a.id}">${a.name}</option>`).join("");
    }
    if (venueSelect) {
      venueSelect.innerHTML = venues.map(v => `<option value="${v.id}">${v.name} (${v.city})</option>`).join("");
    }
    if (tourGroupSelect) {
      tourGroupSelect.innerHTML = tourGroups.map(g =>
        `<option value="${g.id}">${g.name} (${g.artist_name || g.artist})</option>`
      ).join("");
    }
  } catch (err) {
    tourList.innerHTML = `<li class="text-error">${err.message}</li>`;
    window.UI.Toast.error(err.message);
  } finally {
    window.UI.hideLoader(tourList.parentElement);
  }
}

function renderTourItem(tour, actions = []) {
  const actionButtons = actions.map(action => {
    const labels = { archive: "Archive", restore: "Restore", delete: "Delete" };
    return `<button class="btn btn-secondary btn-sm" data-action="${action}" data-id="${tour.id}">${labels[action]}</button>`;
  }).join("");

  return `
    <li class="list-item">
      <div style="flex: 1;">
        <strong>${tour.artist.name}</strong> @ ${tour.venue.name}
        <span class="muted">— ${tour.date}</span>
      </div>
      <div class="list-item-actions">
        ${actionButtons}
      </div>
    </li>
  `;
}

function bindTourForm() {
  const form = document.getElementById("tour-form");
  const errorEl = document.getElementById("tour-error");
  const successEl = document.getElementById("tour-success");
  const dateInput = document.getElementById("tour-date");

  if (!form) return;

  // Set min date
  window.UI.setMinDate(dateInput, 1);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";
    if (successEl) successEl.textContent = "";

    const artistId = document.getElementById("tour-artist").value;
    const tourGroupId = document.getElementById("tour-group")?.value;
    const venueId = document.getElementById("tour-venue").value;
    const date = document.getElementById("tour-date").value;
    const ticketPrice = document.getElementById("tour-price").value;

    if (!artistId || !tourGroupId || !venueId || !date || !ticketPrice) {
      if (errorEl) errorEl.textContent = "Please fill all fields.";
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    window.UI.setButtonLoading(submitBtn, true);

    try {
      await window.API.request("/api/tours/", {
        method: "POST",
        body: JSON.stringify({
          tour_id: Number(tourGroupId),
          artist_id: Number(artistId),
          venue_id: Number(venueId),
          date,
          ticket_price: ticketPrice
        })
      });
      form.reset();
      if (successEl) successEl.textContent = "Tour created successfully!";
      window.UI.Toast.success("Tour date created");
      loadTourDatesPage();
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
      window.UI.Toast.error(err.message);
    } finally {
      window.UI.setButtonLoading(submitBtn, false);
    }
  });
}

function bindTourDateActions() {
  const listContainer = document.getElementById("tour-dates");
  if (!listContainer) return;

  // Toggle archived
  const toggleBtn = document.getElementById("toggle-archived");
  const archivedList = document.getElementById("archived-tour-list");
  if (toggleBtn && archivedList) {
    toggleBtn.addEventListener("click", () => {
      const isHidden = archivedList.style.display === "none";
      archivedList.style.display = isHidden ? "block" : "none";
      toggleBtn.textContent = isHidden ? "Hide" : "Show";
    });
  }

  // Actions
  listContainer.addEventListener("click", async (e) => {
    const actionBtn = e.target.closest("[data-action]");
    if (!actionBtn) return;

    const action = actionBtn.dataset.action;
    const id = Number(actionBtn.dataset.id);

    try {
      if (action === "archive") {
        await window.API.request(`/api/tours/${id}/`, {
          method: "PATCH",
          body: JSON.stringify({ is_archived: true })
        });
        window.UI.Toast.success("Tour archived");
      } else if (action === "restore") {
        await window.API.request(`/api/tours/${id}/`, {
          method: "PATCH",
          body: JSON.stringify({ is_archived: false })
        });
        window.UI.Toast.success("Tour restored");
      } else if (action === "delete") {
        if (!confirm("Delete this tour date?")) return;
        await window.API.request(`/api/tours/${id}/`, { method: "DELETE" });
        window.UI.Toast.success("Tour deleted");
      }
      loadTourDatesPage();
    } catch (err) {
      window.UI.Toast.error(err.message);
    }
  });
}

// Initialize
function initTourDatesPage() {
  window.UI.initPage({
    onLoad: () => {
      loadTourDatesPage();
      bindTourForm();
      bindTourDateActions();
    }
  });
}

window.Pages = window.Pages || {};
window.Pages.tourDates = { init: initTourDatesPage };
