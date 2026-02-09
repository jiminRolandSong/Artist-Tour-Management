/* =============================================================================
   Optimization Detail Page
============================================================================= */

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


function haversineKm(lat1, lon1, lat2, lon2) {
  if ([lat1, lon1, lat2, lon2].some(v => v === null || v === undefined)) return null;
  const toRad = (v) => (Number(v) * Math.PI) / 180;
  const R = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

async function loadOptimizeDetail() {
  const summaryEl = document.getElementById("opt-detail-summary");
  const formulaEl = document.getElementById("opt-detail-formula");
  const tableEl = document.getElementById("opt-detail-table");

  const stored = localStorage.getItem("optimize_last_run");
  if (!stored) {
    if (summaryEl) summaryEl.innerHTML = '<div class="text-error">No optimization data found. Run optimize first.</div>';
    return;
  }

  let data;
  try {
    data = JSON.parse(stored);
  } catch {
    if (summaryEl) summaryEl.innerHTML = '<div class="text-error">Failed to parse optimization data.</div>';
    return;
  }

  const metrics = data.metrics || {};
  const venuesById = new Map((data.venues || []).map(v => [v.id, v]));
  const optimizedRoute = data.optimized_route || [];
  const baselineRoute = data.baseline_route || [];
  const selectionStrategy = data.selection_strategy;
  const selectionRationale = data.selection_rationale;
  const selectionError = data.selection_error;
  const selectedVenueCount = (data.selected_venue_ids || optimizedRoute).length;

  const costPerKm = Number(data.constraints?.cost_per_km || 2.0);
  const optimizedDistance = metrics.optimized_distance_km || 0;
  const travelCost = optimizedDistance ? optimizedDistance * costPerKm : null;
  const operatingCost = optimizedRoute.reduce((sum, id) => {
    const venue = venuesById.get(Number(id));
    return sum + Number(venue?.operating_cost || 0);
  }, 0);
  const totalCost = metrics.estimated_total_cost ?? (travelCost !== null ? travelCost + operatingCost : null);
  const revenue = metrics.estimated_revenue ?? null;

  if (summaryEl) {
    summaryEl.innerHTML = `
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
        <div class="stat-value">${formatCurrency(revenue)}</div>
        <div class="stat-label">Est. revenue</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${formatCurrency(totalCost)}</div>
        <div class="stat-label">Est. cost</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${formatMetric(metrics.estimated_roi, 3)}</div>
        <div class="stat-label">Estimated ROI</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${selectionStrategy || "N/A"}</div>
        <div class="stat-label">Selection</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${formatMetric(selectedVenueCount, 0)}</div>
        <div class="stat-label">Selected venues</div>
      </div>
    `;
  }

  if (formulaEl) {
    formulaEl.innerHTML = `
      Travel cost = optimized distance × cost per km (${formatMetric(optimizedDistance)} × ${formatCurrency(costPerKm)}/km)<br />
      Operating cost = sum of venue operating costs in optimized route<br />
      Total cost = travel cost + operating cost<br />
      Revenue = Σ (fan_count × engagement × ticket_price) capped by venue capacity
      ${selectionRationale ? `<br /><span class="muted">AI rationale: ${selectionRationale}</span>` : ""}
    `;
  }

  if (selectionError && formulaEl) {
    formulaEl.innerHTML += `<br /><span class="text-warning">AI note: ${selectionError}</span>`;
  }

  let fanDemands = [];
  try {
    const allDemands = await window.API.request("/api/fan-demand/");
    fanDemands = allDemands.filter(d => d.artist === data.artist_id);
  } catch {
    fanDemands = [];
  }

  const demandByVenue = new Map(fanDemands.map(d => [d.venue, d]));

  const rows = optimizedRoute.map((id, idx) => {
    const venue = venuesById.get(Number(id));
    const demand = demandByVenue.get(Number(id));
    const capacity = Number(venue?.capacity || 0);
    const fanCount = Number(demand?.fan_count || 0);
    const engagement = Number(demand?.engagement_score || 0);
    const expectedAttendance = capacity ? Math.min(fanCount * engagement, capacity) : fanCount * engagement;
    const ticketPrice = Number(demand?.expected_ticket_price || venue?.default_ticket_price || 0);
    const estRevenue = expectedAttendance * ticketPrice;

    let legDistance = null;
    if (idx < optimizedRoute.length - 1) {
      const nextVenue = venuesById.get(Number(optimizedRoute[idx + 1]));
      if (venue && nextVenue) {
        legDistance = haversineKm(venue.latitude, venue.longitude, nextVenue.latitude, nextVenue.longitude);
      }
    }

    return `
      <tr>
        <td>${idx + 1}</td>
        <td>${normalizeVenueName(venue?.name) || id}</td>
        <td>${venue?.city || "-"}</td>
        <td>${formatCurrency(venue?.operating_cost || 0)}</td>
        <td>${formatMetric(expectedAttendance)}</td>
        <td>${formatCurrency(ticketPrice)}</td>
        <td>${formatCurrency(estRevenue)}</td>
        <td>${legDistance ? formatMetric(legDistance) : "-"}</td>
      </tr>
    `;
  }).join("");

  if (tableEl) {
    tableEl.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Venue</th>
            <th>City</th>
            <th>Operating Cost</th>
            <th>Expected Attendance</th>
            <th>Ticket Price</th>
            <th>Est. Revenue</th>
            <th>Leg Distance (km)</th>
          </tr>
        </thead>
        <tbody>
          ${rows || '<tr><td colspan="8" class="muted">No route data available.</td></tr>'}
        </tbody>
      </table>
    `;
  }

  const mapInstance = window.MapManager?.create("opt-detail-map");
  if (mapInstance) {
    mapInstance.renderRoutes(baselineRoute, optimizedRoute, venuesById);
  }
}

function initOptimizeDetailPage() {
  window.UI.initPage({
    onLoad: () => {
      loadOptimizeDetail();
    }
  });
}

window.Pages = window.Pages || {};
window.Pages.optimizeDetail = { init: initOptimizeDetailPage };
