/* =============================================================================
   Optimize Page Logic
============================================================================= */

let optimizeState = {
  lastRunId: null,
  lastRunSchedule: [],
  venueById: new Map(),
  lastPlanArtistId: null,
  tourGroups: []
};

function formatMetric(value, decimals = 2) {
  if (value === null || value === undefined || value === "") return "N/A";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return num.toLocaleString(undefined, { maximumFractionDigits: decimals, minimumFractionDigits: 0 });
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === "") return "N/A";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return num.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  });
}

function normalizeVenueName(name) {
  if (!name) return name;
  return name.replace(/\s\d{10,}$/g, "").trim();
}

function venueLabelById(id) {
  const venue = optimizeState.venueById.get(Number(id));
  if (!venue) return String(id);
  const name = normalizeVenueName(venue.name);
  const city = venue.city ? ` (${venue.city})` : "";
  return `${name}${city}`;
}

function renderRouteDetails(label, route) {
  const safeRoute = route || [];
  const listItems = safeRoute.map((id) => `<li>${venueLabelById(id)}</li>`).join("");
  return `
    <details class="route-details">
      <summary>${label} (${safeRoute.length} stops)</summary>
      <ol class="route-list">
        ${listItems || "<li class=\"muted\">No route data.</li>"}
      </ol>
    </details>
  `;
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

async function loadOptimizePage() {
  const tourGroupSelect = document.getElementById("opt-tour-group");
  const startCitySelect = document.getElementById("opt-start-city");
  const venueList = document.getElementById("opt-venue-list");
  const confirmTourGroup = document.getElementById("confirm-tour-group");
  const startVenueSelect = document.getElementById("opt-start-venue");
  const startDateInput = document.getElementById("opt-start-date");
  const endDateInput = document.getElementById("opt-end-date");

  if (!tourGroupSelect) return;

  try {
    const tourGroups = await window.API.request("/api/tour-groups/");
    optimizeState.tourGroups = tourGroups;

    tourGroupSelect.innerHTML = tourGroups.map(g =>
      `<option value="${g.id}" data-artist="${g.artist}">${g.name} (${g.artist_name || g.artist})</option>`
    ).join("");

    const updateGroupContext = () => {
      const groupId = Number(tourGroupSelect.value);
      const group = tourGroups.find(g => g.id === groupId);
      const venues = group?.venues || [];

      optimizeState.venueById = new Map(venues.map(v => [v.id, v]));

      if (startDateInput) {
        startDateInput.value = group?.start_date || "";
      }
      if (endDateInput) {
        endDateInput.value = group?.end_date || "";
      }

      if (startCitySelect) {
        const cities = [...new Set(venues.map(v => v.city))];
        startCitySelect.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join("");
      }

      if (startVenueSelect) {
        startVenueSelect.innerHTML = venues.map(v =>
          `<option value="${v.id}">${v.name} (${v.city})</option>`
        ).join("");
      }

      if (venueList) {
        venueList.innerHTML = venues.length
          ? venues.map(v => `
              <label class="checkbox-group">
                <input type="checkbox" value="${v.id}" checked />
                <span>${v.name} <span class="muted">(${v.city})</span></span>
              </label>
            `).join("")
          : '<div class="muted">No venues linked. Assign venues in Tour Groups first.</div>';
      }

      // Update confirm dropdown to only show tour groups for the same artist
      if (confirmTourGroup && group) {
        const sameArtistGroups = tourGroups.filter(g => g.artist === group.artist);
        confirmTourGroup.innerHTML = sameArtistGroups.map(g =>
          `<option value="${g.id}"${g.id === groupId ? ' selected' : ''}>${g.name}</option>`
        ).join("");
      }
    };

    updateGroupContext();
    tourGroupSelect.addEventListener("change", updateGroupContext);
  } catch (err) {
    window.UI.Toast.error(err.message);
  }
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
    const start_city = document.getElementById("opt-start-city").value;
    const start_venue_id = document.getElementById("opt-start-venue").value;
    const min_revenue = document.getElementById("opt-min-revenue").value;
    const min_roi = document.getElementById("opt-min-roi").value;
    const min_attendance = document.getElementById("opt-min-attendance").value;
    const min_gap_days = document.getElementById("opt-min-gap").value;
    const travel_speed = document.getElementById("opt-speed").value;
    const max_venues = document.getElementById("opt-max-venues").value;
    const ai_select = document.getElementById("opt-ai-select").value === "true";
    const venueIds = Array.from(document.querySelectorAll("#opt-venue-list input:checked"))
      .map(i => Number(i.value));

    if (!tourGroupId || !venueIds.length) {
      if (errorEl) errorEl.textContent = "Tour group and venues are required.";
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    window.UI.setButtonLoading(submitBtn, true);

    try {
      const group = optimizeState.tourGroups.find(g => g.id === tourGroupId);

      if (!group) throw new Error("Tour group not found.");
      if (!group.start_date || !group.end_date) {
        throw new Error("Tour group is missing start/end dates.");
      }

      // Generate unique plan name with milliseconds and random suffix
      const now = new Date();
      const timestamp = now.toISOString().replace(/[:.]/g, "").slice(0, 17);
      const randomSuffix = Math.random().toString(36).substring(2, 6);
      const planName = `${group.name} Plan ${timestamp}-${randomSuffix}`;

      // Store the artist ID for confirmation
      optimizeState.lastPlanArtistId = group.artist;

      const plan = await window.API.request("/api/plans/", {
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
            cost_per_km: "2.00",
            distance_weight: "1.0",
            revenue_weight: "1.0",
            max_venues: max_venues ? Number(max_venues) : null,
            use_ai_selection: ai_select,
            start_venue_id: start_venue_id ? Number(start_venue_id) : null
          }
        })
      });

      const run = await window.API.request(`/api/plans/${plan.id}/run/`, { method: "POST" });
      optimizeState.lastRunId = run.id;
      const result = run.result || {};
      const metrics = result.metrics || {};
      optimizeState.lastRunSchedule = result.schedule || [];

      if (resultEl) {
        resultEl.innerHTML = `
          <div class="tag tag-copper">Optimization Complete</div>
          <div style="margin-top: var(--space-md);">
            ${renderRouteDetails("Optimized route", result.optimized_route)}
            ${renderRouteDetails("Baseline route", result.baseline_route)}
            ${result.warnings?.length ? `<div class="text-warning">Warnings: ${result.warnings.join(", ")}</div>` : ""}
            ${result.selection_rationale ? `<div class="muted" style="margin-top: var(--space-sm);">AI rationale: ${result.selection_rationale}</div>` : ""}
          </div>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-value">${formatMetric(metrics.baseline_distance_km)}</div>
              <div class="stat-label">Baseline km</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">${formatMetric(metrics.optimized_distance_km)}</div>
              <div class="stat-label">Optimized km</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">${formatMetric(metrics.distance_reduction_pct)}%</div>
              <div class="stat-label">Distance reduction</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">${formatCurrency(metrics.estimated_revenue)}</div>
              <div class="stat-label">Est. revenue</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">${formatCurrency(metrics.estimated_total_cost)}</div>
              <div class="stat-label">Est. cost</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">${formatMetric(metrics.estimated_roi, 3)}</div>
              <div class="stat-label">Estimated ROI</div>
            </div>
          </div>
          <div style="margin-top: var(--space-sm);">
            <a class="btn btn-secondary btn-sm" href="optimize-detail.html">View detailed metrics</a>
          </div>
        `;
      }

      if (scheduleEl) {
        scheduleEl.innerHTML = `
          <h4 style="margin-top: var(--space-lg);">Edit Schedule</h4>
          <div class="list">
            ${optimizeState.lastRunSchedule.map((s, idx) => {
              const venue = optimizeState.venueById.get(Number(s.venue_id));
              return `
                <div class="list-item">
                  <span style="min-width: 220px;">${venue ? venueLabelById(venue.id) : `Venue ${s.venue_id}`}</span>
                  <input type="date" data-schedule-index="${idx}" value="${s.date}" />
                </div>
              `;
            }).join("")}
          </div>
        `;
      }

      // Update confirm dropdown to only show tour groups for the same artist
      if (confirmTourGroup) {
        const sameArtistGroups = optimizeState.tourGroups.filter(g => g.artist === group.artist);
        confirmTourGroup.innerHTML = sameArtistGroups.map(g =>
          `<option value="${g.id}"${g.id === tourGroupId ? ' selected' : ''}>${g.name}</option>`
        ).join("");
      }

      // Render map
      const mapInstance = window.MapManager?.create("opt-map");
      if (mapInstance) {
        mapInstance.renderRoutes(
          result.baseline_route,
          result.optimized_route,
          optimizeState.venueById
        );
      }

      const detailPayload = {
        generated_at: new Date().toISOString(),
        artist_id: group.artist,
        tour_group_id: group.id,
        plan_name: planName,
        constraints: {
          cost_per_km: 2.0,
          distance_weight: 1.0,
          revenue_weight: 1.0,
          min_gap_days: Number(min_gap_days || 1),
          travel_speed_km_per_day: Number(travel_speed || 500),
          start_venue_id: start_venue_id ? Number(start_venue_id) : null
        },
        metrics,
        baseline_route: result.baseline_route || [],
        optimized_route: result.optimized_route || [],
        selected_venue_ids: result.selected_venue_ids || [],
        selection_strategy: result.selection_strategy || null,
        selection_rationale: result.selection_rationale || null,
        selection_error: result.selection_error || null,
        venues: Array.from(optimizeState.venueById.values())
      };
      localStorage.setItem("optimize_last_run", JSON.stringify(detailPayload));
      appendRunHistory({
        run_id: run.id,
        plan_id: plan.id,
        artist_id: group.artist,
        tour_group_id: group.id,
        created_at: new Date().toISOString(),
        selection_strategy: result.selection_strategy || null,
        selection_rationale: result.selection_rationale || null,
        selection_error: result.selection_error || null,
        metrics
      });

      window.UI.Toast.success("Optimization complete");
      if (confirmResult) confirmResult.textContent = "";
    } catch (err) {
      if (errorEl) errorEl.textContent = err.message;
      window.UI.Toast.error(err.message);
    } finally {
      window.UI.setButtonLoading(submitBtn, false);
    }
  });

  if (confirmBtn) {
    confirmBtn.addEventListener("click", async () => {
      if (!optimizeState.lastRunId) {
        if (confirmResult) confirmResult.textContent = "Run optimization first.";
        return;
      }
      const tourId = confirmTourGroup?.value;
      if (!tourId) {
        if (confirmResult) confirmResult.textContent = "Select a tour group.";
        return;
      }

      // Verify the selected tour group belongs to the same artist as the plan
      const selectedGroup = optimizeState.tourGroups.find(g => g.id === Number(tourId));
      if (selectedGroup && optimizeState.lastPlanArtistId && selectedGroup.artist !== optimizeState.lastPlanArtistId) {
        if (confirmResult) confirmResult.textContent = "Selected tour group must belong to the same artist.";
        return;
      }

      const editedSchedule = optimizeState.lastRunSchedule.map((s, idx) => {
        const input = document.querySelector(`[data-schedule-index="${idx}"]`);
        return {
          venue_id: s.venue_id,
          date: input ? input.value : s.date
        };
      });

      window.UI.setButtonLoading(confirmBtn, true);

      try {
        const payload = {
          tour_id: Number(tourId),
          conflict_strategy: confirmStrategy?.value || null,
          schedule: editedSchedule
        };
        const res = await window.API.request(`/api/runs/${optimizeState.lastRunId}/confirm/`, {
          method: "POST",
          body: JSON.stringify(payload)
        });

        if (confirmResult) {
          confirmResult.innerHTML = `<span class="text-success">Confirmed. Created ${res.created_tour_ids.length} dates.</span>`;
        }
        window.UI.Toast.success(`Created ${res.created_tour_ids.length} tour dates`);
      } catch (err) {
        if (confirmResult) confirmResult.textContent = err.message;
        window.UI.Toast.error(err.message);
      } finally {
        window.UI.setButtonLoading(confirmBtn, false);
      }
    });
  }
}

// Initialize
function initOptimizePage() {
  window.UI.initPage({
    onLoad: () => {
      loadOptimizePage();
      bindOptimizeFlow();
    }
  });
}

window.Pages = window.Pages || {};
window.Pages.optimize = { init: initOptimizePage };
