const API_BASE = "http://127.0.0.1:8000";

function saveToken(token) {
  localStorage.setItem("access_token", token);
}

function getToken() {
  return localStorage.getItem("access_token");
}

function clearToken() {
  localStorage.removeItem("access_token");
}

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

  return res.json();
}

function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

let mapInstance = null;
let mapLayer = null;
let lastRunId = null;
let lastRunSchedule = [];

function parseISODate(value) {
  if (!value) return null;
  return new Date(`${value}T00:00:00`);
}

function getToday() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function renderInsights(tours) {
  const insightsEl = document.getElementById("tour-insights");
  if (!insightsEl) return;

  if (!tours.length) {
    insightsEl.textContent = "No tours yet. Create your first tour to see insights.";
    return;
  }

  const today = getToday();
  const upcoming = tours.filter((t) => parseISODate(t.date) >= today);
  const past = tours.filter((t) => parseISODate(t.date) < today);
  const nextTour = upcoming.sort((a, b) => parseISODate(a.date) - parseISODate(b.date))[0];
  const avgPrice =
    tours.reduce((sum, t) => sum + Number(t.ticket_price || 0), 0) / tours.length;

  insightsEl.innerHTML = `
    <div>Total tours: <strong>${tours.length}</strong></div>
    <div>Upcoming: <strong>${upcoming.length}</strong> | Past: <strong>${past.length}</strong></div>
    <div>Next tour: <strong>${nextTour ? nextTour.date : "N/A"}</strong></div>
    <div>Avg ticket price: <strong>$${avgPrice.toFixed(2)}</strong></div>
  `;
}

function renderMap(tours) {
  const mapEl = document.getElementById("tour-map");
  if (!mapEl || typeof L === "undefined") return;

  const coords = tours
    .map((t) => ({
      lat: t.venue?.latitude,
      lon: t.venue?.longitude,
      label: `${t.artist?.name} @ ${t.venue?.name} (${t.date})`
    }))
    .filter((c) => c.lat && c.lon);

  if (!mapInstance) {
    mapInstance = L.map("tour-map").setView([20, 0], 2);
    mapLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(mapInstance);
  }

  mapLayer && mapLayer.addTo(mapInstance);
  mapInstance.eachLayer((layer) => {
    if (layer instanceof L.Marker) {
      mapInstance.removeLayer(layer);
    }
  });

  if (!coords.length) {
    return;
  }

  const bounds = [];
  coords.forEach((c) => {
    const marker = L.marker([Number(c.lat), Number(c.lon)]).addTo(mapInstance);
    marker.bindPopup(c.label);
    bounds.push([Number(c.lat), Number(c.lon)]);
  });

  if (bounds.length > 1) {
    mapInstance.fitBounds(bounds, { padding: [30, 30] });
  } else {
    mapInstance.setView(bounds[0], 6);
  }
}

async function loadHomeSummary() {
  const upcomingList = document.getElementById("upcoming-tour-list");
  const summaryEl = document.getElementById("upcoming-summary");
  if (!upcomingList || !summaryEl) return;

  try {
    const tourDates = await apiRequest("/api/tours/");
    const today = getToday();
    const upcoming = tourDates
      .filter((t) => parseISODate(t.date) >= today)
      .sort((a, b) => parseISODate(a.date) - parseISODate(b.date));

    summaryEl.textContent = `${upcoming.length} upcoming dates`;
    upcomingList.innerHTML = upcoming.length
      ? upcoming.slice(0, 10).map((t) => `<li>${t.artist.name} @ ${t.venue.name} — ${t.date}</li>`).join("")
      : "<li>No upcoming tours.</li>";

    renderInsights(tourDates);
    renderMap(tourDates);
  } catch (err) {
    summaryEl.textContent = "Failed to load tours.";
    upcomingList.innerHTML = `<li>${err.message}</li>`;
  }
}

async function loadArtistsPage() {
  const artistList = document.getElementById("artist-list");
  if (!artistList) return;

  try {
    const artistDetails = document.getElementById("artist-details");
    const artistGroups = document.getElementById("artist-groups");
    const artistTours = document.getElementById("artist-tours");

    const [artists, tourDates, tourGroups] = await Promise.all([
      apiRequest("/api/artists/"),
      apiRequest("/api/tours/"),
      apiRequest("/api/tour-groups/")
    ]);

    const artistsById = new Map(artists.map((a) => [a.id, a]));

    artistList.innerHTML = artists.length
      ? artists
          .map(
            (a) =>
              `<li>
                <button class="btn btn-secondary artist-item" data-id="${a.id}">${a.name}</button>
                <span class="muted">(${a.genre})</span>
                <button class="btn btn-secondary" data-action="edit" data-id="${a.id}">Edit</button>
                <button class="btn btn-secondary" data-action="delete" data-id="${a.id}">Delete</button>
              </li>`
          )
          .join("")
      : "<li>No artists yet.</li>";

    const showArtist = (artistId) => {
      const artist = artistsById.get(artistId);
      if (!artist) return;

      if (artistDetails) {
        artistDetails.innerHTML = `
          <h4 style="margin: 0 0 8px;">${artist.name}</h4>
          <div class="muted">Genre: ${artist.genre}</div>
        `;
      }

      const groups = tourGroups.filter((g) => g.artist === artistId);
      const dates = tourDates.filter((t) => t.artist.id === artistId);

      if (artistGroups) {
        artistGroups.innerHTML = groups.length
          ? groups.map((g) => `<li>${g.name}</li>`).join("")
          : "<li>No tour groups yet.</li>";
      }

      if (artistTours) {
        artistTours.innerHTML = dates.length
          ? dates.map((t) => `<li>${t.venue.name} — ${t.date}</li>`).join("")
          : "<li>No tour dates yet.</li>";
      }
    };

    if (artists[0]) {
      showArtist(artists[0].id);
    }

    artistList.querySelectorAll(".artist-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        showArtist(Number(btn.dataset.id));
      });
    });
  } catch (err) {
    artistList.innerHTML = `<li>${err.message}</li>`;
    const artistDetails = document.getElementById("artist-details");
    if (artistDetails) artistDetails.textContent = "Failed to load artist details.";
  }
}

async function loadTourGroupsPage() {
  const tourGroupList = document.getElementById("tour-group-list");
  const tourGroupArtistSelect = document.getElementById("tour-group-artist");
  const venueTourGroupSelect = document.getElementById("venue-tour-group");
  const venuePickList = document.getElementById("venue-pick-list");
  if (!tourGroupList || !tourGroupArtistSelect) return;

  try {
    const [tourGroups, artists, venues] = await Promise.all([
      apiRequest("/api/tour-groups/"),
      apiRequest("/api/artists/"),
      apiRequest("/api/venues/")
    ]);

    tourGroupList.innerHTML = tourGroups.length
      ? tourGroups
          .map(
            (g) =>
              `<li><a class="btn btn-secondary" href="tour-group.html?id=${g.id}">${g.name}</a> <span class="muted">(${g.artist_name || g.artist})</span></li>`
          )
          .join("")
      : "<li>No tour groups yet.</li>";

    tourGroupArtistSelect.innerHTML = artists.map((a) => `<option value="${a.id}">${a.name}</option>`).join("");

    if (venueTourGroupSelect) {
      venueTourGroupSelect.innerHTML = tourGroups
        .map((g) => `<option value="${g.id}">${g.name} (${g.artist_name || g.artist})</option>`)
        .join("");
    }

    if (venuePickList) {
      venuePickList.innerHTML = venues.length
        ? venues
            .map(
              (v) =>
                `<label style="display:flex;gap:8px;align-items:center;">
                  <input type="checkbox" value="${v.id}" />
                  <span>${v.name} <span class="muted">(${v.city})</span></span>
                </label>`
            )
            .join("")
        : "<div class=\"muted\">No venues yet.</div>";
    }
  } catch (err) {
    tourGroupList.innerHTML = `<li>${err.message}</li>`;
  }
}

function bindTourGroupVenueForm() {
  const form = document.getElementById("tour-group-venues-form");
  const errorEl = document.getElementById("venue-assign-error");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";

    const tourGroupId = document.getElementById("venue-tour-group").value;
    const venueIds = Array.from(document.querySelectorAll("#venue-pick-list input:checked")).map((v) =>
      Number(v.value)
    );

    if (!tourGroupId || !venueIds.length) {
      if (errorEl) errorEl.textContent = "Select a tour group and at least one venue.";
      return;
    }

    try {
      await apiRequest(`/api/tour-groups/${tourGroupId}/`, {
        method: "PATCH",
        body: JSON.stringify({ venue_ids: venueIds })
      });
      if (errorEl) errorEl.textContent = "Saved. Use Optimize page to build schedule.";
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
    }
  });
}

async function loadTourGroupDetail() {
  const groupId = Number(getQueryParam("id"));
  const titleEl = document.getElementById("tour-group-title");
  const metaEl = document.getElementById("tour-group-meta");
  const datesEl = document.getElementById("tour-group-dates");
  const venuesEl = document.getElementById("tour-group-venues");
  const aiEl = document.getElementById("tour-group-ai");
  const analysisEl = document.getElementById("tour-group-analysis");
  const runBtn = document.getElementById("run-optimization");

  if (!groupId) {
    if (titleEl) titleEl.textContent = "No tour group selected.";
    return;
  }

  try {
    const [groups, tourDates] = await Promise.all([
      apiRequest("/api/tour-groups/"),
      apiRequest("/api/tours/")
    ]);

    const group = groups.find((g) => g.id === groupId);
    if (!group) {
      if (titleEl) titleEl.textContent = "Tour group not found.";
      return;
    }

    const dates = tourDates.filter((t) => {
      const tid = Number(t.tour_id_read || t.tour_id);
      return tid === groupId;
    });
    const uniqueVenues = Array.from(
      new Map(dates.map((d) => [d.venue.id, d.venue])).values()
    );

    if (titleEl) titleEl.textContent = group.name;
    if (metaEl) {
      metaEl.innerHTML = `
        <div class="muted">Artist: ${group.artist_name || group.artist}</div>
        <div class="muted">Start: ${group.start_date || "N/A"} | End: ${group.end_date || "N/A"}</div>
      `;
    }

    const artistInfoEl = document.getElementById("tour-group-artists");
    if (artistInfoEl) {
      artistInfoEl.textContent = group.artist_name || group.artist;
    }

    if (datesEl) {
      datesEl.innerHTML = dates.length
        ? dates.map((d) => `<li>${d.venue.name} — ${d.date}</li>`).join("")
        : "<li>No tour dates yet.</li>";
    }

    if (venuesEl) {
      venuesEl.innerHTML = uniqueVenues.length
        ? uniqueVenues.map((v) => `<li>${v.name} <span class="muted">(${v.city})</span></li>`).join("")
        : "<li>No venues linked yet.</li>";
    }

    if (aiEl) {
      aiEl.textContent = "AI optimization results will appear here after you run it.";
    }

    if (analysisEl) {
      const avgPrice = dates.length
        ? dates.reduce((sum, d) => sum + Number(d.ticket_price || 0), 0) / dates.length
        : 0;
      analysisEl.innerHTML = `
        <div>Total dates: <strong>${dates.length}</strong></div>
        <div>Unique venues: <strong>${uniqueVenues.length}</strong></div>
        <div>Avg ticket price: <strong>$${avgPrice.toFixed(2)}</strong></div>
      `;
    }

    if (runBtn) {
      runBtn.onclick = async () => {
        if (!dates.length) {
          if (aiEl) aiEl.textContent = "No dates available to optimize.";
          return;
        }

        const venueIds = uniqueVenues.map((v) => v.id);
        const startCity = uniqueVenues[0]?.city || "";

        try {
          if (aiEl) aiEl.textContent = "Running optimization...";
          const payload = {
            artist_id: group.artist,
            venue_ids: venueIds,
            start_city: startCity,
            use_ai: true,
            cost_per_km: "2.00",
            distance_weight: "1.0",
            revenue_weight: "1.0",
            start_date: group.start_date || null,
            min_gap_days: 1,
            travel_speed_km_per_day: "500"
          };
          const result = await apiRequest("/api/optimize/", {
            method: "POST",
            body: JSON.stringify(payload)
          });

          if (aiEl) {
            aiEl.innerHTML = `
              <div>Optimized route: <strong>${result.optimized_route.join(" → ")}</strong></div>
              <div>Distance reduction: <strong>${result.metrics.distance_reduction_pct ?? "N/A"}%</strong></div>
              <div>Estimated ROI: <strong>${result.metrics.estimated_roi ?? "N/A"}</strong></div>
            `;
          }
        } catch (err) {
          if (aiEl) aiEl.textContent = err.message;
        }
      };
    }
  } catch (err) {
    if (titleEl) titleEl.textContent = "Failed to load tour group.";
  }
}

async function loadTourDatesPage() {
  const tourList = document.getElementById("tour-list");
  const pastTourList = document.getElementById("past-tour-list");
  const archivedTourList = document.getElementById("archived-tour-list");
  const venueSelect = document.getElementById("tour-venue");
  const artistSelect = document.getElementById("tour-artist");
  const tourGroupSelect = document.getElementById("tour-group");

  if (!tourList || !pastTourList || !archivedTourList) return;

  try {
    const [tourDates, venues, artists, tourGroups] = await Promise.all([
      apiRequest("/api/tours/"),
      apiRequest("/api/venues/"),
      apiRequest("/api/artists/"),
      apiRequest("/api/tour-groups/")
    ]);

    const today = getToday();
    const activeTours = tourDates.filter((t) => !t.is_archived);
    const upcomingTours = activeTours.filter((t) => parseISODate(t.date) >= today);
    const pastTours = activeTours.filter((t) => parseISODate(t.date) < today);
    const archivedTours = tourDates.filter((t) => t.is_archived);

    tourList.innerHTML = upcomingTours.length
      ? upcomingTours
          .map(
            (t) =>
              `<li>
                ${t.artist.name} @ ${t.venue.name} — ${t.date}
                <button class="btn btn-secondary" data-action="archive" data-id="${t.id}">Archive</button>
                <button class="btn btn-secondary" data-action="delete" data-id="${t.id}">Delete</button>
              </li>`
          )
          .join("")
      : "<li>No upcoming tours.</li>";

    pastTourList.innerHTML = pastTours.length
      ? pastTours
          .map(
            (t) =>
              `<li>
                ${t.artist.name} @ ${t.venue.name} — ${t.date}
                <button class="btn btn-secondary" data-action="archive" data-id="${t.id}">Archive</button>
                <button class="btn btn-secondary" data-action="delete" data-id="${t.id}">Delete</button>
              </li>`
          )
          .join("")
      : "<li>No past tours.</li>";

    archivedTourList.innerHTML = archivedTours.length
      ? archivedTours
          .map(
            (t) =>
              `<li>
                ${t.artist.name} @ ${t.venue.name} — ${t.date}
                <button class="btn btn-secondary" data-action="restore" data-id="${t.id}">Restore</button>
                <button class="btn btn-secondary" data-action="delete" data-id="${t.id}">Delete</button>
              </li>`
          )
          .join("")
      : "<li>No archived tours.</li>";

    if (artistSelect) {
      artistSelect.innerHTML = artists.map((a) => `<option value="${a.id}">${a.name}</option>`).join("");
    }
    if (venueSelect) {
      venueSelect.innerHTML = venues.map((v) => `<option value="${v.id}">${v.name} (${v.city})</option>`).join("");
    }
    if (tourGroupSelect) {
      tourGroupSelect.innerHTML = tourGroups
        .map((g) => `<option value="${g.id}">${g.name} (${g.artist_name || g.artist})</option>`)
        .join("");
    }
  } catch (err) {
    tourList.innerHTML = `<li>${err.message}</li>`;
    pastTourList.innerHTML = `<li>${err.message}</li>`;
    archivedTourList.innerHTML = `<li>${err.message}</li>`;
  }
}

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

function requireAuth() {
  if (!getToken()) {
    window.location.href = "login.html";
  }
}

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
      if (errorEl) errorEl.textContent = "Please enter username and password.";
      return;
    }

    try {
      await login(username, password);
      window.location.href = "home.html";
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
    }
  });
}

function bindRegisterForm() {
  const form = document.querySelector("form");
  const errorEl = document.querySelector(".signup-error");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";

    const username = document.getElementById("username").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!username || !email || !password) {
      if (errorEl) errorEl.textContent = "Please fill in all fields.";
      return;
    }

    try {
      await register(username, email, password);
      await login(username, password);
      window.location.href = "home.html";
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
    }
  });
}

function bindArtistForm() {
  const form = document.getElementById("artist-form");
  const errorEl = document.getElementById("artist-error");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";

    const name = document.getElementById("artist-name").value.trim();
    const genre = document.getElementById("artist-genre").value.trim();
    if (!name || !genre) {
      if (errorEl) errorEl.textContent = "Please enter name and genre.";
      return;
    }

    try {
      await apiRequest("/api/artists/", {
        method: "POST",
        body: JSON.stringify({ name, genre })
      });
      form.reset();
      loadDashboard();
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
    }
  });
}

function bindArtistActions() {
  const artistList = document.getElementById("artist-list");
  if (!artistList) return;

  artistList.addEventListener("click", async (e) => {
    const editBtn = e.target.closest("[data-action='edit']");
    const deleteBtn = e.target.closest("[data-action='delete']");
    if (!editBtn && !deleteBtn) return;

    const artistId = Number((editBtn || deleteBtn).dataset.id);
    if (deleteBtn) {
      if (!confirm("Delete this artist? This will remove linked tours.")) return;
      try {
        await apiRequest(`/api/artists/${artistId}/`, { method: "DELETE" });
        loadArtistsPage();
      } catch (err) {
        alert(err.message);
      }
    }

    if (editBtn) {
      const name = prompt("New artist name?");
      const genre = prompt("New genre?");
      if (!name || !genre) return;
      try {
        await apiRequest(`/api/artists/${artistId}/`, {
          method: "PATCH",
          body: JSON.stringify({ name, genre })
        });
        loadArtistsPage();
      } catch (err) {
        alert(err.message);
      }
    }
  });
}

function bindTourForm() {
  const form = document.getElementById("tour-form");
  const errorEl = document.getElementById("tour-error");
  const successEl = document.getElementById("tour-success");
  const dateInput = document.getElementById("tour-date");
  const tourGroupSelect = document.getElementById("tour-group");
  if (!form) return;

  if (dateInput) {
    const today = getToday();
    const minDate = new Date(today.getTime() + 24 * 60 * 60 * 1000);
    dateInput.min = minDate.toISOString().split("T")[0];
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";
    if (successEl) successEl.textContent = "";

    const artistId = document.getElementById("tour-artist").value;
    const tourGroupId = tourGroupSelect ? tourGroupSelect.value : null;
    const venueId = document.getElementById("tour-venue").value;
    const date = document.getElementById("tour-date").value;
    const ticketPrice = document.getElementById("tour-price").value;

    if (!artistId || !tourGroupId || !venueId || !date || !ticketPrice) {
      if (errorEl) errorEl.textContent = "Fill all fields.";
      return;
    }

    try {
      await apiRequest("/api/tours/", {
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
      if (successEl) successEl.textContent = "Tour created. Insights and map updated.";
      loadDashboard();
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
    }
  });
}

function bindTourDateActions() {
  const listContainer = document.getElementById("tour-dates");
  const toggleBtn = document.getElementById("toggle-archived");
  const archivedList = document.getElementById("archived-tour-list");
  if (!listContainer) return;

  if (toggleBtn && archivedList) {
    toggleBtn.addEventListener("click", () => {
      const isHidden = archivedList.style.display === "none";
      archivedList.style.display = isHidden ? "block" : "none";
      toggleBtn.textContent = isHidden ? "Hide" : "Show";
    });
  }

  listContainer.addEventListener("click", async (e) => {
    const actionBtn = e.target.closest("[data-action]");
    if (!actionBtn) return;
    const action = actionBtn.dataset.action;
    const id = Number(actionBtn.dataset.id);

    try {
      if (action === "archive") {
        await apiRequest(`/api/tours/${id}/`, {
          method: "PATCH",
          body: JSON.stringify({ is_archived: true })
        });
      } else if (action === "restore") {
        await apiRequest(`/api/tours/${id}/`, {
          method: "PATCH",
          body: JSON.stringify({ is_archived: false })
        });
      } else if (action === "delete") {
        if (!confirm("Delete this tour date?")) return;
        await apiRequest(`/api/tours/${id}/`, { method: "DELETE" });
      }
      loadTourDatesPage();
    } catch (err) {
      alert(err.message);
    }
  });
}

function bindTourGroupForm() {
  const form = document.getElementById("tour-group-form");
  const errorEl = document.getElementById("tour-group-error");
  const startInput = document.getElementById("tour-group-start");
  if (!form) return;

  if (startInput) {
    const today = getToday();
    const minDate = new Date(today.getTime() + 24 * 60 * 60 * 1000);
    startInput.min = minDate.toISOString().split("T")[0];
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";

    const name = document.getElementById("tour-group-name").value.trim();
    const artistId = document.getElementById("tour-group-artist").value;
    const startDate = document.getElementById("tour-group-start").value || null;
    const endDate = document.getElementById("tour-group-end").value || null;
    const desc = document.getElementById("tour-group-desc").value.trim();

    if (!name || !artistId) {
      if (errorEl) errorEl.textContent = "Please provide a tour name and artist.";
      return;
    }

    try {
      await apiRequest("/api/tour-groups/", {
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
      loadTourGroupsPage();
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
    }
  });
}

async function loadOptimizePage() {
  const tourGroupSelect = document.getElementById("opt-tour-group");
  const startCitySelect = document.getElementById("opt-start-city");
  const venueList = document.getElementById("opt-venue-list");
  const confirmTourGroup = document.getElementById("confirm-tour-group");
  const startVenueSelect = document.getElementById("opt-start-venue");
  const startDateInput = document.getElementById("opt-start-date");
  const endDateInput = document.getElementById("opt-end-date");
  if (!tourGroupSelect || !startCitySelect || !venueList || !confirmTourGroup) return;

  const [tourGroups, tourDates] = await Promise.all([
    apiRequest("/api/tour-groups/"),
    apiRequest("/api/tours/")
  ]);

  tourGroupSelect.innerHTML = tourGroups
    .map((g) => `<option value="${g.id}">${g.name} (${g.artist_name || g.artist})</option>`)
    .join("");
  confirmTourGroup.innerHTML = tourGroups
    .map((g) => `<option value="${g.id}">${g.name} (${g.artist_name || g.artist})</option>`)
    .join("");

  const updateGroupContext = () => {
    const groupId = Number(tourGroupSelect.value);
    const group = tourGroups.find((g) => g.id === groupId);
    const venues = group && group.venues ? group.venues : [];

    if (startDateInput) {
      startDateInput.value = group && group.start_date ? group.start_date : "";
    }
    if (endDateInput) {
      endDateInput.value = group && group.end_date ? group.end_date : "";
    }

    startCitySelect.innerHTML = venues
      .map((v) => `<option value="${v.city}">${v.city}</option>`)
      .filter((v, i, arr) => arr.indexOf(v) === i)
      .join("");

    if (startVenueSelect) {
      startVenueSelect.innerHTML = venues
        .map((v) => `<option value="${v.id}">${v.name} (${v.city})</option>`)
        .join("");
    }

    venueList.innerHTML = venues.length
      ? venues
          .map(
            (v) =>
              `<label style="display:flex;gap:8px;align-items:center;">
                <input type="checkbox" value="${v.id}" checked />
                <span>${v.name} <span class="muted">(${v.city})</span></span>
              </label>`
          )
          .join("")
      : "<div class=\"muted\">No venues linked yet. Assign venues in Tour Groups first.</div>";
  };

  updateGroupContext();
  tourGroupSelect.addEventListener("change", updateGroupContext);
}

function bindOptimizeFlow() {
  const form = document.getElementById("opt-form");
  const errorEl = document.getElementById("opt-error");
  const resultEl = document.getElementById("plan-result");
  const scheduleEl = document.getElementById("opt-schedule");
  const confirmBtn = document.getElementById("confirm-run");
  const confirmResult = document.getElementById("confirm-result");
  const confirmTourGroup = document.getElementById("confirm-tour-group");
  const confirmStrategy = document.getElementById("confirm-strategy");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorEl) errorEl.textContent = "";

    const tourGroupId = Number(document.getElementById("opt-tour-group").value);
    const start_date = document.getElementById("opt-start-date").value;
    const end_date = document.getElementById("opt-end-date").value;
    const start_city = document.getElementById("opt-start-city").value;
    const start_venue_id = document.getElementById("opt-start-venue").value;
    const min_revenue = document.getElementById("opt-min-revenue").value;
    const min_roi = document.getElementById("opt-min-roi").value;
    const min_attendance = document.getElementById("opt-min-attendance").value;
    const min_gap_days = document.getElementById("opt-min-gap").value;
    const travel_speed = document.getElementById("opt-speed").value;
    const venueIds = Array.from(document.querySelectorAll("#opt-venue-list input:checked")).map((i) => Number(i.value));

    if (!tourGroupId || !venueIds.length) {
      if (errorEl) errorEl.textContent = "Tour group and venues are required.";
      return;
    }

    try {
      const tourGroups = await apiRequest("/api/tour-groups/");
      const group = tourGroups.find((g) => g.id === tourGroupId);
      if (!group) {
        throw new Error("Tour group not found.");
      }
      if (!group.start_date || !group.end_date) {
        throw new Error("This tour group is missing start/end dates.");
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, "").slice(0, 15);
      const planName = `${group.name} Plan ${timestamp}`;
      const plan = await apiRequest("/api/plans/", {
        method: "POST",
        body: JSON.stringify({
          name: planName,
          artist: group.artist,
          start_date: group.start_date,
          end_date: group.end_date,
          start_city,
          venue_ids: venueIds,
          region_filters: {},
          targets: {
            min_revenue: min_revenue || null,
            min_roi: min_roi || null,
            min_attendance: min_attendance || null
          },
          constraints: {
            min_gap_days: min_gap_days || 1,
            travel_speed_km_per_day: travel_speed || 500,
            start_venue_id: start_venue_id ? Number(start_venue_id) : null
          }
        })
      });

      const run = await apiRequest(`/api/plans/${plan.id}/run/`, { method: "POST" });
      lastRunId = run.id;
      const result = run.result || {};
      const metrics = result.metrics || {};
      lastRunSchedule = result.schedule || [];

      if (resultEl) {
        const startVenue = start_venue_id ? `Start venue: ${start_venue_id}` : "Start venue: Auto";
        resultEl.innerHTML = `
          <div>${startVenue}</div>
          <div>Optimized route: <strong>${(result.optimized_route || []).join(" → ")}</strong></div>
          <div>Distance reduction: <strong>${metrics.distance_reduction_pct ?? "N/A"}%</strong></div>
          <div>Estimated ROI: <strong>${metrics.estimated_roi ?? "N/A"}</strong></div>
          <div>Warnings: <strong>${(result.warnings || []).join(", ") || "None"}</strong></div>
        `;
      }

      if (scheduleEl) {
        scheduleEl.innerHTML = `
          <h4 style="margin-top: 16px;">Edit Schedule</h4>
          <div class="list">
            ${lastRunSchedule
              .map(
                (s, idx) =>
                  `<label style="display:flex;gap:8px;align-items:center;">
                    <span style="min-width:120px;">Venue ${s.venue_id}</span>
                    <input type="date" data-schedule-index="${idx}" value="${s.date}" />
                  </label>`
              )
              .join("")}
          </div>
        `;
      }

      if (confirmResult) confirmResult.textContent = "";
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
    }
  });

  if (confirmBtn) {
    confirmBtn.addEventListener("click", async () => {
      if (!lastRunId) {
        if (confirmResult) confirmResult.textContent = "Run AI first.";
        return;
      }
      const tourId = confirmTourGroup ? confirmTourGroup.value : null;
      if (!tourId) {
        if (confirmResult) confirmResult.textContent = "Select a tour group.";
        return;
      }

      const editedSchedule = lastRunSchedule.map((s, idx) => {
        const input = document.querySelector(`[data-schedule-index=\"${idx}\"]`);
        return {
          venue_id: s.venue_id,
          date: input ? input.value : s.date
        };
      });

      try {
        const payload = {
          tour_id: Number(tourId),
          conflict_strategy: confirmStrategy && confirmStrategy.value ? confirmStrategy.value : null,
          schedule: editedSchedule
        };
        const res = await apiRequest(`/api/runs/${lastRunId}/confirm/`, {
          method: "POST",
          body: JSON.stringify(payload)
        });
        if (confirmResult) {
          confirmResult.textContent = `Confirmed. Created ${res.created_tour_ids.length} dates.`;
        }
      } catch (err) {
        if (confirmResult) confirmResult.textContent = err.message;
      }
    });
  }
}
function bindLogout() {
  const logoutBtn = document.getElementById("logout");
  if (!logoutBtn) return;
  logoutBtn.addEventListener("click", () => {
    clearToken();
    window.location.href = "login.html";
  });
}

window.AppAuth = {
  bindLoginForm,
  bindRegisterForm,
  bindArtistForm,
  bindArtistActions,
  bindTourForm,
  bindTourGroupForm,
  bindTourGroupVenueForm,
  bindTourDateActions,
  loadHomeSummary,
  loadArtistsPage,
  loadTourGroupsPage,
  loadTourDatesPage,
  loadTourGroupDetail,
  loadOptimizePage,
  bindOptimizeFlow,
  requireAuth,
  bindLogout
};
