/* =============================================================================
   Tour Group Detail Page Logic
============================================================================= */

async function loadTourGroupDetail() {
  const groupId = Number(window.UI.getQueryParam("id"));
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
      window.API.request("/api/tour-groups/"),
      window.API.request("/api/tours/")
    ]);

    const group = groups.find(g => g.id === groupId);
    if (!group) {
      if (titleEl) titleEl.textContent = "Tour group not found.";
      return;
    }

    const dates = tourDates.filter(t => {
      const tid = Number(t.tour_id_read || t.tour_id);
      return tid === groupId;
    });
    const uniqueVenues = Array.from(
      new Map(dates.map(d => [d.venue.id, d.venue])).values()
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
        ? dates.map(d => `<li>${d.venue.name} — ${d.date}</li>`).join("")
        : '<li class="muted">No tour dates yet.</li>';
    }

    if (venuesEl) {
      venuesEl.innerHTML = uniqueVenues.length
        ? uniqueVenues.map(v => `<li>${v.name} <span class="muted">(${v.city})</span></li>`).join("")
        : '<li class="muted">No venues linked yet.</li>';
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

        const venueIds = uniqueVenues.map(v => v.id);
        const startCity = uniqueVenues[0]?.city || "";

        try {
          if (aiEl) aiEl.innerHTML = '<div class="spinner"></div> Running optimization...';

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
          const result = await window.API.request("/api/optimize/", {
            method: "POST",
            body: JSON.stringify(payload)
          });

          if (aiEl) {
            aiEl.innerHTML = `
              <div>Optimized route: <strong>${result.optimized_route.join(" → ")}</strong></div>
              <div>Distance reduction: <strong>${result.metrics.distance_reduction_pct ?? "N/A"}%</strong></div>
              <div>Estimated ROI: <strong>${result.metrics.estimated_roi ?? "N/A"}</strong></div>
              ${result.selection_strategy ? `<div>Selection: <strong>${result.selection_strategy}</strong></div>` : ""}
              ${result.selection_rationale ? `<div class="muted">AI rationale: ${result.selection_rationale}</div>` : ""}
            `;
          }
          appendRunHistory({
            run_id: null,
            plan_id: null,
            artist_id: group.artist,
            tour_group_id: group.id,
            created_at: new Date().toISOString(),
            selection_strategy: result.selection_strategy || null,
            selection_rationale: result.selection_rationale || null,
            selection_error: result.selection_error || null,
            metrics: result.metrics || {}
          });
          window.UI.Toast.success("Optimization complete");
        } catch (err) {
          if (aiEl) aiEl.textContent = err.message;
          window.UI.Toast.error(err.message);
        }
      };
    }
  } catch (err) {
    if (titleEl) titleEl.textContent = "Failed to load tour group.";
    window.UI.Toast.error(err.message);
  }
}

function appendRunHistory(entry) {
  const key = "optimize_run_history";
  let history = [];
  try {
    const stored = localStorage.getItem(key);
    history = stored ? JSON.parse(stored) : [];
    if (!Array.isArray(history)) history = [];
  } catch {
    history = [];
  }
  history.unshift(entry);
  localStorage.setItem(key, JSON.stringify(history.slice(0, 50)));
}

// Initialize
function initTourGroupDetailPage() {
  window.UI.initPage({
    onLoad: loadTourGroupDetail
  });
}

window.Pages = window.Pages || {};
window.Pages.tourGroupDetail = { init: initTourGroupDetailPage };
