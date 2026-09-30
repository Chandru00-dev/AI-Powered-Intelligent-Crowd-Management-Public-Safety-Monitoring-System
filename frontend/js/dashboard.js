/**
 * AI Crowd Management & Public Safety Monitoring System
 * Dashboard Page Controller
 */

import { ApiClient } from './api.js';
import { AuthService } from './auth.js';
import { Toast, escapeHtml } from './utils.js';

let crowdChartInstance = null;

export async function initDashboard() {
  const user = await AuthService.verifySession();
  if (!user) return;

  await loadDashboardData();
  // Poll summary every 15 seconds to keep dashboard fresh
  setInterval(loadDashboardData, 15000);
}

async function loadDashboardData() {
  try {
    const summary = await ApiClient.get('/dashboard/summary');
    renderSummaryCards(summary);
    renderPreviewFeed(summary);
    renderCrowdChart(summary);
    renderRecentAlerts(summary.recent_alerts);
    renderZoneStatus(summary.zones);
  } catch (err) {
    console.error('Failed to load dashboard metrics:', err);
    Toast.error('Unable to fetch live dashboard telemetry.');
  }
}

function renderSummaryCards(data) {
  // Stat counters
  const totalCamsEl = document.getElementById('stat-total-cams');
  const onlineCamsEl = document.getElementById('stat-online-cams');
  const currentPeopleEl = document.getElementById('stat-current-people');
  const activeAlertsEl = document.getElementById('stat-active-alerts');
  const systemStatusEl = document.getElementById('stat-system-status');
  const dbStatusEl = document.getElementById('stat-db-status');

  if (totalCamsEl) totalCamsEl.textContent = data.total_cameras;
  if (onlineCamsEl) onlineCamsEl.textContent = `${data.online_cameras} / ${data.total_cameras}`;
  if (currentPeopleEl) currentPeopleEl.textContent = data.current_people;
  if (activeAlertsEl) activeAlertsEl.textContent = data.active_alerts;
  if (systemStatusEl) systemStatusEl.textContent = data.system_status;
  if (dbStatusEl) dbStatusEl.textContent = data.database_type;

  // Section 20 Telemetry Bar
  const telePeople = document.getElementById('tele-people');
  const teleDensity = document.getElementById('tele-density');
  const teleCongestion = document.getElementById('tele-congestion');
  const teleAlerts = document.getElementById('tele-alerts');

  if (telePeople) telePeople.textContent = data.current_people;
  if (teleDensity) {
    teleDensity.textContent = data.current_people > 40 ? 'HIGH' : (data.current_people > 20 ? 'MEDIUM' : 'LOW');
    teleDensity.className = `telemetry-value ${data.current_people > 40 ? 'telemetry-val-amber' : 'telemetry-val-green'}`;
  }
  if (teleCongestion) {
    const cong = data.congestion_level || (data.current_people > 45 ? 'CONGESTED' : 'NORMAL');
    teleCongestion.textContent = cong;
    teleCongestion.className = `telemetry-value ${cong === 'SEVERE' || cong === 'CONGESTED' ? 'telemetry-val-red' : (cong === 'MODERATE' ? 'telemetry-val-amber' : 'telemetry-val-green')}`;
  }
  if (teleAlerts) teleAlerts.textContent = data.active_alerts;
}

function renderPreviewFeed(data) {
  const streamImg = document.getElementById('dashboard-stream-img');
  const previewCamName = document.getElementById('dashboard-stream-cam-name');
  if (!streamImg) return;

  if (data.recent_cameras && data.recent_cameras.length > 0) {
    const firstCam = data.recent_cameras[0];
    if (previewCamName) previewCamName.textContent = firstCam.name;
    // Set non-blocking stream endpoint
    streamImg.src = `/api/cameras/${firstCam.id}/stream`;
  } else {
    if (previewCamName) previewCamName.textContent = "No Camera Configured";
    streamImg.src = "";
  }
}

function renderCrowdChart(data) {
  const canvas = document.getElementById('crowdChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const labels = data.crowd_chart_labels || ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00"];
  const counts = data.crowd_chart_data || [12, 19, 35, 48, 52, 41, 38];

  if (crowdChartInstance) {
    crowdChartInstance.data.labels = labels;
    crowdChartInstance.data.datasets[0].data = counts;
    crowdChartInstance.update();
    return;
  }

  // Create gradient
  const gradient = ctx.createLinearGradient(0, 0, 0, 260);
  gradient.addColorStop(0, 'rgba(6, 182, 212, 0.4)');
  gradient.addColorStop(1, 'rgba(6, 182, 212, 0.0)');

  // @ts-ignore (Chart.js is loaded via CDN in HTML)
  crowdChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'People Count',
        data: counts,
        borderColor: '#06b6d4',
        borderWidth: 3,
        backgroundColor: gradient,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: '#06b6d4',
        pointBorderColor: '#fff',
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1e293b',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          titleColor: '#f8fafc',
          bodyColor: '#06b6d4',
          displayColors: false
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } },
          beginAtZero: true
        }
      }
    }
  });
}

function renderRecentAlerts(alerts) {
  const container = document.getElementById('recent-alerts-tbody');
  if (!container) return;

  if (!alerts || alerts.length === 0) {
    container.innerHTML = `
      <tr>
        <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">
          <i class="fas fa-shield-check" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block; color: var(--status-online);"></i>
          No critical alerts recorded. All sectors nominal.
        </td>
      </tr>
    `;
    return;
  }

  container.innerHTML = alerts.map(a => {
    let badgeClass = 'badge-warning';
    if (a.severity === 'CRITICAL') badgeClass = 'badge-critical';
    if (a.severity === 'LOW') badgeClass = 'badge-offline';

    return `
      <tr>
        <td><span style="font-family: var(--font-mono); font-size: 0.8rem;">${escapeHtml(a.timestamp)}</span></td>
        <td><strong>${escapeHtml(a.camera_name)}</strong></td>
        <td>${escapeHtml(a.message)}</td>
        <td><span class="badge ${badgeClass}">${escapeHtml(a.severity)}</span></td>
      </tr>
    `;
  }).join('');
}

function renderZoneStatus(zones) {
  const container = document.getElementById('dashboard-zone-list');
  if (!container || !zones || zones.length === 0) return;

  container.innerHTML = zones.map(z => {
    let badgeClass = 'badge-online';
    let label = z.density_level;
    if (z.density_level === 'CRITICAL') {
      badgeClass = 'badge-critical';
      label = 'Critical Congestion';
    } else if (z.density_level === 'HIGH') {
      badgeClass = 'badge-critical';
      label = 'High Density';
    } else if (z.density_level === 'MEDIUM') {
      badgeClass = 'badge-warning';
      label = 'Medium Density';
    } else {
      badgeClass = 'badge-online';
      label = 'Low / Normal';
    }

    const pct = Math.round(z.occupancy_ratio * 100);

    return `
      <div class="zone-item">
        <div>
          <div class="zone-info-title">${escapeHtml(z.name)}</div>
          <div class="zone-info-sub">Count: ${z.people_count} / Cap: ${z.capacity} (${pct}%)</div>
        </div>
        <span class="badge ${badgeClass}">${escapeHtml(label)}</span>
      </div>
    `;
  }).join('');
}

