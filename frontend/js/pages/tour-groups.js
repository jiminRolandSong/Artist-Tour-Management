/* =============================================================================
   Tour Groups Page Logic
============================================================================= */

let tourGroupsPageData = {
  tourGroups: [],
  artists: [],
  venues: []
};

// Continent mapping based on country
const continentMap = {
  // Europe
  'UK': 'Europe', 'United Kingdom': 'Europe', 'England': 'Europe', 'Scotland': 'Europe',
  'Germany': 'Europe', 'France': 'Europe', 'Spain': 'Europe', 'Italy': 'Europe',
  'Netherlands': 'Europe', 'Belgium': 'Europe', 'Switzerland': 'Europe', 'Austria': 'Europe',
  'Sweden': 'Europe', 'Norway': 'Europe', 'Denmark': 'Europe', 'Finland': 'Europe',
  'Poland': 'Europe', 'Czech Republic': 'Europe', 'Portugal': 'Europe', 'Ireland': 'Europe',
  'Greece': 'Europe', 'Hungary': 'Europe', 'Romania': 'Europe', 'Croatia': 'Europe',
  // Asia
  'Japan': 'Asia', 'South Korea': 'Asia', 'Korea': 'Asia', 'China': 'Asia', 'Taiwan': 'Asia',
  'Thailand': 'Asia', 'Singapore': 'Asia', 'Malaysia': 'Asia', 'Indonesia': 'Asia',
  'Philippines': 'Asia', 'Vietnam': 'Asia', 'India': 'Asia', 'Hong Kong': 'Asia',
  // North America
  'USA': 'North America', 'United States': 'North America', 'US': 'North America',
  'Canada': 'North America', 'Mexico': 'North America',
  // South America
  'Brazil': 'South America', 'Argentina': 'South America', 'Chile': 'South America',
  'Colombia': 'South America', 'Peru': 'South America',
  // Oceania
  'Australia': 'Oceania', 'New Zealand': 'Oceania',
  // Africa
  'South Africa': 'Africa', 'Egypt': 'Africa', 'Morocco': 'Africa', 'Nigeria': 'Africa',
  // Middle East
  'UAE': 'Middle East', 'United Arab Emirates': 'Middle East', 'Israel': 'Middle East',
  'Saudi Arabia': 'Middle East', 'Qatar': 'Middle East', 'Turkey': 'Middle East'
};

function getContinent(venue) {
  const country = venue.country || '';
  return continentMap[country] || 'Other';
}

function groupVenuesByContinent(venues) {
  const groups = {};
  venues.forEach(v => {
    const continent = getContinent(v);
    if (!groups[continent]) groups[continent] = [];
    groups[continent].push(v);
  });
  // Sort continents
  const order = ['North America', 'Europe', 'Asia', 'Oceania', 'South America', 'Africa', 'Middle East', 'Other'];
  const sorted = {};
  order.forEach(c => {
    if (groups[c]) sorted[c] = groups[c];
  });
  return sorted;
}

async function loadTourGroupsPage() {
  const tourGroupList = document.getElementById("tour-group-list");
  const tourGroupArtistSelect = document.getElementById("tour-group-artist");
  const venueTourGroupSelect = document.getElementById("venue-tour-group");
  const venuePickList = document.getElementById("venue-pick-list");

  if (!tourGroupList) return;

  window.UI.showLoader(tourGroupList.parentElement);

  try {
    const [tourGroups, artists, venues] = await Promise.all([
      window.API.request("/api/tour-groups/"),
      window.API.request("/api/artists/"),
      window.API.request("/api/venues/")
    ]);

    tourGroupsPageData = { tourGroups, artists, venues };

    // Render tour groups list with edit/delete buttons
    tourGroupList.innerHTML = tourGroups.length
      ? tourGroups.map(g => `
          <li class="list-item">
            <a href="tour-group.html?id=${g.id}" style="flex: 1; text-decoration: none; color: inherit;">
              <strong>${g.name}</strong>
              <span class="muted"> — ${g.artist_name || g.artist}</span>
            </a>
            <div class="list-item-actions">
              <button class="btn btn-secondary btn-sm" data-action="edit" data-id="${g.id}">Edit</button>
              <button class="btn btn-danger btn-sm" data-action="delete" data-id="${g.id}">Delete</button>
            </div>
          </li>
        `).join("")
      : '<li class="muted">No tour groups yet. Create one below.</li>';

    // Populate artist select
    if (tourGroupArtistSelect) {
      tourGroupArtistSelect.innerHTML = artists.map(a =>
        `<option value="${a.id}">${a.name}</option>`
      ).join("");
    }

    // Populate tour group select for venue assignment
    if (venueTourGroupSelect) {
      venueTourGroupSelect.innerHTML = tourGroups.map(g =>
        `<option value="${g.id}">${g.name} (${g.artist_name || g.artist})</option>`
      ).join("");
    }

    // Populate venue pick list grouped by continent
    if (venuePickList) {
      const grouped = groupVenuesByContinent(venues);
      let html = '';
      for (const [continent, venueList] of Object.entries(grouped)) {
        html += `<div class="venue-continent-group">
          <div class="venue-continent-header">${continent} (${venueList.length})</div>
          ${venueList.map(v => `
            <label class="checkbox-group">
              <input type="checkbox" value="${v.id}" />
              <span>${v.name} <span class="muted">(${v.city})</span></span>
            </label>
          `).join("")}
        </div>`;
      }
      venuePickList.innerHTML = html || '<div class="muted">No venues available.</div>';
    }
  } catch (err) {
    tourGroupList.innerHTML = `<li class="text-error">${err.message}</li>`;
    window.UI.Toast.error(err.message);
  } finally {
    window.UI.hideLoader(tourGroupList.parentElement);
  }
}

function bindTourGroupForm() {
  const form = document.getElementById("tour-group-form");
  const errorEl = document.getElementById("tour-group-error");
  const startInput = document.getElementById("tour-group-start");

  if (!form) return;

  window.UI.setMinDate(startInput, 1);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";

    const name = document.getElementById("tour-group-name").value.trim();
    const artistId = document.getElementById("tour-group-artist").value;
    const startDate = document.getElementById("tour-group-start").value || null;
    const endDate = document.getElementById("tour-group-end").value || null;
    const desc = document.getElementById("tour-group-desc")?.value.trim() || "";

    if (!name || !artistId) {
      if (errorEl) errorEl.textContent = "Please provide a tour name and artist.";
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    window.UI.setButtonLoading(submitBtn, true);

    try {
      await window.API.request("/api/tour-groups/", {
        method: "POST",
        body: JSON.stringify({
          name,
          artist: Number(artistId),
          start_date: startDate,
          end_date: endDate,
          description: desc
        })
      });
      form.reset();
      window.UI.Toast.success("Tour group created");
      loadTourGroupsPage();
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
      window.UI.Toast.error(err.message);
    } finally {
      window.UI.setButtonLoading(submitBtn, false);
    }
  });
}

function bindTourGroupVenueForm() {
  const form = document.getElementById("tour-group-venues-form");
  const errorEl = document.getElementById("venue-assign-error");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";

    const tourGroupId = document.getElementById("venue-tour-group").value;
    const venueIds = Array.from(document.querySelectorAll("#venue-pick-list input:checked"))
      .map(v => Number(v.value));

    if (!tourGroupId || !venueIds.length) {
      if (errorEl) errorEl.textContent = "Select a tour group and at least one venue.";
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    window.UI.setButtonLoading(submitBtn, true);

    try {
      await window.API.request(`/api/tour-groups/${tourGroupId}/`, {
        method: "PATCH",
        body: JSON.stringify({ venue_ids: venueIds })
      });
      window.UI.Toast.success("Venues assigned. Use Optimize page to build schedule.");
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
      window.UI.Toast.error(err.message);
    } finally {
      window.UI.setButtonLoading(submitBtn, false);
    }
  });
}

function bindTourGroupActions() {
  const tourGroupList = document.getElementById("tour-group-list");
  if (!tourGroupList) return;

  tourGroupList.addEventListener("click", async (e) => {
    const editBtn = e.target.closest("[data-action='edit']");
    const deleteBtn = e.target.closest("[data-action='delete']");
    if (!editBtn && !deleteBtn) return;

    e.preventDefault();
    const groupId = Number((editBtn || deleteBtn).dataset.id);
    const group = tourGroupsPageData.tourGroups.find(g => g.id === groupId);

    if (deleteBtn) {
      if (!confirm(`Delete tour group "${group?.name}"? This cannot be undone.`)) return;
      try {
        await window.API.request(`/api/tour-groups/${groupId}/`, { method: "DELETE" });
        window.UI.Toast.success("Tour group deleted");
        loadTourGroupsPage();
      } catch (err) {
        window.UI.Toast.error(err.message);
      }
    }

    if (editBtn) {
      const name = prompt("New tour group name:", group?.name || "");
      if (!name) return;

      try {
        await window.API.request(`/api/tour-groups/${groupId}/`, {
          method: "PATCH",
          body: JSON.stringify({ name })
        });
        window.UI.Toast.success("Tour group updated");
        loadTourGroupsPage();
      } catch (err) {
        window.UI.Toast.error(err.message);
      }
    }
  });
}

// Initialize
function initTourGroupsPage() {
  window.UI.initPage({
    onLoad: () => {
      loadTourGroupsPage();
      bindTourGroupForm();
      bindTourGroupVenueForm();
      bindTourGroupActions();
    }
  });
}

window.Pages = window.Pages || {};
window.Pages.tourGroups = { init: initTourGroupsPage };
