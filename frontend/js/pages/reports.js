/* =============================================================================
   Reports Page Logic
============================================================================= */

async function loadReportsPage() {
  const reportType = document.getElementById("report-type");
  const artistSelect = document.getElementById("report-artist");
  const generateBtn = document.getElementById("generate-report");
  const reportOutput = document.getElementById("report-output");

  if (!reportType) return;

  try {
    const artists = await window.API.request("/api/artists/");

    if (artistSelect) {
      artistSelect.innerHTML = '<option value="">All Artists</option>' +
        artists.map(a => `<option value="${a.id}">${a.name}</option>`).join("");
    }
  } catch (err) {
    window.UI.Toast.error(err.message);
  }

  if (generateBtn) {
    generateBtn.addEventListener("click", async () => {
      const type = reportType.value;
      const artistId = artistSelect?.value;

      window.UI.setButtonLoading(generateBtn, true);

      try {
        let endpoint = "/api/reports/";
        const params = new URLSearchParams();
        params.append("type", type);
        if (artistId) params.append("artist", artistId);

        const report = await window.API.request(`${endpoint}?${params.toString()}`);

        if (reportOutput) {
          renderReport(reportOutput, type, report);
        }

        window.UI.Toast.success("Report generated");
      } catch (err) {
        if (reportOutput) {
          reportOutput.innerHTML = `<div class="text-error">${err.message}</div>`;
        }
        window.UI.Toast.error(err.message);
      } finally {
        window.UI.setButtonLoading(generateBtn, false);
      }
    });
  }
}

function renderReport(container, type, data) {
  switch (type) {
    case "revenue":
      container.innerHTML = `
        <h4>Revenue Report</h4>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">$${(data.total_revenue || 0).toLocaleString()}</div>
            <div class="stat-label">Total Revenue</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${data.total_shows || 0}</div>
            <div class="stat-label">Total Shows</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">$${(data.avg_revenue || 0).toLocaleString()}</div>
            <div class="stat-label">Avg per Show</div>
          </div>
        </div>
        ${data.by_artist ? `
          <h5 style="margin-top: var(--space-lg);">By Artist</h5>
          <div class="list">
            ${data.by_artist.map(a => `
              <div class="list-item">
                <span>${a.name}</span>
                <span>$${(a.revenue || 0).toLocaleString()}</span>
              </div>
            `).join("")}
          </div>
        ` : ""}
      `;
      break;

    case "attendance":
      container.innerHTML = `
        <h4>Attendance Report</h4>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">${(data.total_attendance || 0).toLocaleString()}</div>
            <div class="stat-label">Total Attendance</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${data.total_shows || 0}</div>
            <div class="stat-label">Total Shows</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${Math.round(data.avg_attendance || 0).toLocaleString()}</div>
            <div class="stat-label">Avg per Show</div>
          </div>
        </div>
      `;
      break;

    case "venues":
      container.innerHTML = `
        <h4>Venue Performance</h4>
        <div class="list">
          ${(data.venues || []).map(v => `
            <div class="list-item">
              <div>
                <strong>${v.name}</strong>
                <div class="muted">${v.city}</div>
              </div>
              <div class="text-right">
                <div>${v.shows || 0} shows</div>
                <div class="muted">$${(v.revenue || 0).toLocaleString()}</div>
              </div>
            </div>
          `).join("")}
        </div>
      `;
      break;

    default:
      container.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
  }
}

// Initialize
function initReportsPage() {
  window.UI.initPage({
    onLoad: loadReportsPage
  });
}

window.Pages = window.Pages || {};
window.Pages.reports = { init: initReportsPage };
