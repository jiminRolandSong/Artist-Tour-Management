/* =============================================================================
   Artists Page Logic
============================================================================= */

let artistsData = {
  artists: [],
  tourDates: [],
  tourGroups: []
};

async function loadArtistsPage() {
  const artistList = document.getElementById("artist-list");
  if (!artistList) return;

  window.UI.showLoader(artistList.parentElement);

  try {
    const [artists, tourDates, tourGroups] = await Promise.all([
      window.API.request("/api/artists/"),
      window.API.request("/api/tours/"),
      window.API.request("/api/tour-groups/")
    ]);

    artistsData = {
      artists: [...artists].sort((a, b) => a.name.localeCompare(b.name)),
      tourDates,
      tourGroups,
      artistsById: new Map(artists.map(a => [a.id, a]))
    };

    renderArtistList(artistsData.artists);

    if (artistsData.artists[0]) {
      showArtistDetails(artistsData.artists[0].id);
    }
  } catch (err) {
    artistList.innerHTML = `<li class="text-error">${err.message}</li>`;
    window.UI.Toast.error(err.message);
  } finally {
    window.UI.hideLoader(artistList.parentElement);
  }
}

function renderArtistList(artists) {
  const artistList = document.getElementById("artist-list");
  if (!artistList) return;

  artistList.innerHTML = artists.length
    ? artists.map(a => `
        <li class="list-item">
          <div style="flex: 1;">
            <button class="btn btn-secondary artist-item" data-id="${a.id}" style="width: 100%; justify-content: flex-start;">
              ${a.name}
              <span class="muted" style="margin-left: auto;">${a.genre}</span>
            </button>
          </div>
          <div class="list-item-actions">
            <button class="btn btn-secondary btn-sm" data-action="edit" data-id="${a.id}">Edit</button>
            <button class="btn btn-secondary btn-sm" data-action="delete" data-id="${a.id}">Delete</button>
          </div>
        </li>
      `).join("")
    : '<li class="muted">No artists yet. Add one below.</li>';

  // Bind click handlers
  artistList.querySelectorAll(".artist-item").forEach(btn => {
    btn.addEventListener("click", () => {
      showArtistDetails(Number(btn.dataset.id));
      const modal = document.getElementById("artist-modal");
      if (modal) modal.classList.remove("hidden");
    });
  });
}

function showArtistDetails(artistId) {
  const artist = artistsData.artistsById.get(artistId);
  if (!artist) return;

  const detailsEl = document.getElementById("artist-details");
  const groupsEl = document.getElementById("artist-groups");
  const toursEl = document.getElementById("artist-tours");
  const modalContent = document.getElementById("artist-modal-content");
  const groupsSection = document.getElementById("artist-groups-section");
  const toursSection = document.getElementById("artist-tours-section");

  const groups = artistsData.tourGroups.filter(g => g.artist === artistId);
  const dates = artistsData.tourDates.filter(t => t.artist.id === artistId);

  if (detailsEl) {
    detailsEl.innerHTML = `
      <h4 style="margin: 0 0 var(--space-sm);">${artist.name}</h4>
      <div class="muted">Genre: ${artist.genre}</div>
    `;
  }

  if (groupsSection) groupsSection.classList.remove("hidden");
  if (toursSection) toursSection.classList.remove("hidden");

  if (groupsEl) {
    groupsEl.innerHTML = groups.length
      ? groups.map(g => `<li>${g.name}</li>`).join("")
      : '<li class="muted">No tour groups yet.</li>';
  }

  if (toursEl) {
    toursEl.innerHTML = dates.length
      ? dates.map(t => `<li>${t.venue.name} - ${t.date}</li>`).join("")
      : '<li class="muted">No tour dates yet.</li>';
  }

  if (modalContent) {
    modalContent.innerHTML = `
      <h3 style="margin-top:0;">${artist.name}</h3>
      <div class="muted">Genre: ${artist.genre}</div>
      <h4 style="margin: var(--space-md) 0 var(--space-sm);">Tour Groups</h4>
      <ul class="list">
        ${groups.length ? groups.map(g => `<li>${g.name}</li>`).join("") : '<li class="muted">No tour groups yet.</li>'}
      </ul>
      <h4 style="margin: var(--space-md) 0 var(--space-sm);">Tour Dates</h4>
      <ul class="list">
        ${dates.length ? dates.map(t => `<li>${t.venue.name} - ${t.date}</li>`).join("") : '<li class="muted">No tour dates yet.</li>'}
      </ul>
    `;
  }
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

    const submitBtn = form.querySelector('button[type="submit"]');
    window.UI.setButtonLoading(submitBtn, true);

    try {
      await window.API.request("/api/artists/", {
        method: "POST",
        body: JSON.stringify({ name, genre })
      });
      form.reset();
      window.UI.Toast.success("Artist added successfully");
      loadArtistsPage();
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
      window.UI.Toast.error(err.message);
    } finally {
      window.UI.setButtonLoading(submitBtn, false);
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
        await window.API.request(`/api/artists/${artistId}/`, { method: "DELETE" });
        window.UI.Toast.success("Artist deleted");
        loadArtistsPage();
      } catch (err) {
        window.UI.Toast.error(err.message);
      }
    }

    if (editBtn) {
      const artist = artistsData.artistsById.get(artistId);
      const name = prompt("New artist name?", artist?.name || "");
      const genre = prompt("New genre?", artist?.genre || "");
      if (!name || !genre) return;

      try {
        await window.API.request(`/api/artists/${artistId}/`, {
          method: "PATCH",
          body: JSON.stringify({ name, genre })
        });
        window.UI.Toast.success("Artist updated");
        loadArtistsPage();
      } catch (err) {
        window.UI.Toast.error(err.message);
      }
    }
  });
}

function bindModalClose() {
  const modal = document.getElementById("artist-modal");
  if (!modal) return;

  modal.addEventListener("click", (e) => {
    if (e.target.closest("[data-action='close']")) {
      modal.classList.add("hidden");
    }
  });
}

function bindArtistSearch() {
  const searchInput = document.getElementById("artist-search");
  if (!searchInput) return;

  searchInput.addEventListener("input", () => {
    const term = searchInput.value.trim().toLowerCase();
    const filtered = term
      ? artistsData.artists.filter(a =>
          a.name.toLowerCase().includes(term) || a.genre.toLowerCase().includes(term)
        )
      : artistsData.artists;
    renderArtistList(filtered);
  });
}

// Initialize
function initArtistsPage() {
  window.UI.initPage({
    onLoad: () => {
      loadArtistsPage();
      bindArtistForm();
      bindArtistActions();
      bindModalClose();
      bindArtistSearch();
    }
  });
}

window.Pages = window.Pages || {};
window.Pages.artists = { init: initArtistsPage };
