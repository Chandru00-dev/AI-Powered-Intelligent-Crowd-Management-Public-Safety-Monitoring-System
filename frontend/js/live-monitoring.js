/**
 * AI Crowd Management & Public Safety Monitoring System
 * Live Monitoring Console Controller (Phase 4 Enabled)
 */

import { ApiClient } from './api.js';
import { AuthService } from './auth.js';
import { Toast, escapeHtml } from './utils.js';

let activeCameraId = null;
let allCameras = [];
let isPaused = false;
let aiBoxesEnabled = true;
let heatmapEnabled = false;
let telemetryTimer = null;

export async function initLiveMonitoring() {
  const user = await AuthService.verifySession();
  if (!user) return;

  setupControls();
  await loadAvailableCameras();

  // Start telemetry polling loop
  startTelemetryPolling();
}

function setupControls() {
  // AI Boxes Toggle
  const aiBtn = document.getElementById('btn-toggle-ai');
  if (aiBtn) {
    aiBtn.addEventListener('click', () => {
      aiBoxesEnabled = !aiBoxesEnabled;
      aiBtn.className = `btn btn-sm ${aiBoxesEnabled ? 'btn-primary' : 'btn-secondary'}`;
      aiBtn.innerHTML = `<i class="fas fa-draw-polygon"></i> AI Boxes: ${aiBoxesEnabled ? 'ON' : 'OFF'}`;
      refreshStreamFeed();
    });
  }

  // Heatmap Toggle (Phase 4)
  const heatmapBtn = document.getElementById('btn-toggle-heatmap');
  if (heatmapBtn) {
    heatmapBtn.addEventListener('click', () => {
      heatmapEnabled = !heatmapEnabled;
      heatmapBtn.className = `btn btn-sm ${heatmapEnabled ? 'btn-primary' : 'btn-secondary'}`;
      heatmapBtn.innerHTML = `<i class="fas fa-fire"></i> Heatmap: ${heatmapEnabled ? 'ON' : 'OFF'}`;
      refreshStreamFeed();
    });
  }

  // Pause/Resume Stream
  const pauseBtn = document.getElementById('btn-pause-stream');
  if (pauseBtn) {
    pauseBtn.addEventListener('click', toggleStreamPause);
  }

  // Fullscreen
  const fsBtn = document.getElementById('btn-fullscreen-stream');
  if (fsBtn) {
    fsBtn.addEventListener('click', toggleFullscreen);
  }

  // Snapshot Capture
  const snapBtn = document.getElementById('btn-snapshot-stream');
  if (snapBtn) {
    snapBtn.addEventListener('click', captureSnapshot);
  }
}

function getStreamUrl(cameraId) {
  if (!cameraId) return '';
  return `/api/cameras/${cameraId}/stream?annotate=${aiBoxesEnabled}&heatmap=${heatmapEnabled}&t=${Date.now()}`;
}

function refreshStreamFeed() {
  const streamImg = document.getElementById('active-live-stream');
  if (!streamImg || !activeCameraId || isPaused) return;
  // @ts-ignore
  streamImg.src = getStreamUrl(activeCameraId);
}

async function loadAvailableCameras() {
  try {
    allCameras = await ApiClient.get('/cameras', { enabled_only: true });
    renderCameraSelector(allCameras);

    // Check URL parameters for specific camera
    const urlParams = new URLSearchParams(window.location.search);
    const requestedId = parseInt(urlParams.get('camera_id'));

    if (requestedId && allCameras.some(c => c.id === requestedId)) {
      switchCamera(requestedId);
    } else if (allCameras.length > 0) {
      switchCamera(allCameras[0].id);
    } else {
      showEmptyState();
    }
  } catch (err) {
    console.error('Failed to load cameras for live monitoring:', err);
    Toast.error('Unable to initialize live video monitoring channels.');
  }
}

function renderCameraSelector(cameras) {
  const container = document.getElementById('camera-select-list');
  if (!container) return;

  if (cameras.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem;">
        No active surveillance nodes found.<br>
        <a href="cameras.html" style="color: var(--accent-cyan); display: inline-block; margin-top: 0.5rem;">Configure Cameras</a>
      </div>
    `;
    return;
  }

  container.innerHTML = cameras.map(c => `
    <div class="camera-select-item ${c.id === activeCameraId ? 'active' : ''}" onclick="window.selectLiveCamera(${c.id})">
      <div class="select-item-name">
        <span>${escapeHtml(c.name)}</span>
        <span class="badge ${c.status === 'ONLINE' ? 'badge-online' : 'badge-offline'}">${c.status}</span>
      </div>
      <div class="select-item-sub">
        <i class="fas fa-map-marker-alt"></i> ${escapeHtml(c.location)} &bull; ${c.input_type}
      </div>
    </div>
  `).join('');
}

export function switchCamera(cameraId) {
  const camera = allCameras.find(c => c.id === cameraId);
  if (!camera) return;

  activeCameraId = cameraId;
  isPaused = false;

  // Update UI selection classes
  renderCameraSelector(allCameras);

  // Update stream header
  const titleEl = document.getElementById('live-stream-title');
  const locationEl = document.getElementById('live-stream-location');
  const statusEl = document.getElementById('live-stream-status');
  const streamImg = document.getElementById('active-live-stream');

  if (titleEl) titleEl.textContent = camera.name;
  if (locationEl) locationEl.textContent = `${camera.location} (${camera.input_type})`;
  if (statusEl) {
    statusEl.textContent = camera.status;
    statusEl.className = `badge ${camera.status === 'ONLINE' ? 'badge-online' : 'badge-offline'}`;
  }

  if (streamImg) {
    // Connect to backend MJPEG stream with current annotate/heatmap params
    // @ts-ignore
    streamImg.src = getStreamUrl(camera.id);
    streamImg.style.display = 'block';
  }

  // Update telemetry HUD
  const hudRes = document.getElementById('hud-resolution');
  const hudFps = document.getElementById('hud-fps');
  if (hudRes) hudRes.textContent = camera.resolution || '640x360';
  if (hudFps) hudFps.textContent = camera.fps ? `${camera.fps} FPS` : '20 FPS';

  // Immediately poll telemetry for this camera
  pollCameraTelemetry();
}

function startTelemetryPolling() {
  if (telemetryTimer) clearInterval(telemetryTimer);
  telemetryTimer = setInterval(pollCameraTelemetry, 2000);
}

async function pollCameraTelemetry() {
  if (!activeCameraId || isPaused) return;

  // Poll metrics
  try {
    const metrics = await ApiClient.get(`/cameras/${activeCameraId}/metrics`);
    updateLiveMetrics(metrics);
  } catch (e) {
    // Silently continue if camera node is warming up
  }

  // Poll Phase 4 zones
  try {
    const zones = await ApiClient.get(`/cameras/${activeCameraId}/zones`);
    renderZoneBreakdown(zones);
  } catch (e) {
    // Silently continue
  }

  // Poll Phase 5 Congestion & Bottlenecks
  try {
    const congestion = await ApiClient.get(`/cameras/${activeCameraId}/congestion`);
    updateCongestionTelemetry(congestion);
  } catch (e) {
    // Silently continue
  }
}

function updateLiveMetrics(metrics) {
  const peopleEl = document.getElementById('live-tele-people');
  const peakEl = document.getElementById('live-tele-peak');
  const speedEl = document.getElementById('live-tele-speed');
  const hudFps = document.getElementById('hud-fps');
  const tracksBadge = document.getElementById('active-tracks-badge');
  const tracksContainer = document.getElementById('active-tracks-list');

  if (peopleEl) peopleEl.textContent = metrics.current_people ?? 0;
  if (peakEl) peakEl.textContent = metrics.peak_people ?? 0;
  if (hudFps && metrics.fps) hudFps.textContent = `${metrics.fps} FPS`;

  const tracks = metrics.active_tracks || [];
  if (tracksBadge) tracksBadge.textContent = `${tracks.length} Active`;

  // Calculate average velocity
  if (tracks.length > 0) {
    const avgSpeed = (tracks.reduce((acc, t) => acc + (t.movement_speed || 0), 0) / tracks.length).toFixed(1);
    if (speedEl) speedEl.textContent = `${avgSpeed} px/s`;
  } else {
    if (speedEl) speedEl.textContent = '0.0 px/s';
  }

  // Render tracks chips
  if (tracksContainer) {
    if (tracks.length === 0) {
      tracksContainer.innerHTML = `<span style="color: var(--text-muted); font-size: 0.72rem;">No targets currently tracked.</span>`;
    } else {
      tracksContainer.innerHTML = tracks.slice(0, 10).map(t => `
        <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 0.35rem 0.5rem; border-radius: 4px; border-left: 2px solid var(--accent-cyan);">
          <span style="font-weight: 600; font-family: var(--font-mono); color: var(--accent-cyan);">ID #${t.id}</span>
          <span style="color: var(--text-muted); font-size: 0.7rem;">${escapeHtml(t.direction || 'STAT')} &bull; ${t.movement_speed || 0} px/s</span>
          <span style="font-size: 0.7rem; color: #94a3b8;">${t.duration_sec || 0}s</span>
        </div>
      `).join('');
    }
  }
}

function renderZoneBreakdown(zones) {
  const container = document.getElementById('live-zone-breakdown');
  if (!container || !zones) return;

  const zoneKeys = Object.keys(zones);
  if (zoneKeys.length === 0) {
    container.innerHTML = `<span style="color: var(--text-muted); font-size: 0.72rem;">Zone partitions initializing...</span>`;
    return;
  }

  container.innerHTML = zoneKeys.map(key => {
    const z = zones[key];
    const pct = Math.min(Math.round((z.occupancy_ratio || 0) * 100), 100);

    let badgeClass = 'badge-online';
    let barColor = '#10b981';
    if (z.density_level === 'CRITICAL') {
      badgeClass = 'badge-critical';
      barColor = '#ef4444';
    } else if (z.density_level === 'HIGH') {
      badgeClass = 'badge-critical';
      barColor = '#f97316';
    } else if (z.density_level === 'MEDIUM') {
      badgeClass = 'badge-warning';
      barColor = '#f59e0b';
    }

    return `
      <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); padding: 0.6rem; border-radius: 6px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
          <strong style="color: #f1f5f9; font-size: 0.75rem;">${escapeHtml(z.name || key)}</strong>
          <span class="badge ${badgeClass}" style="font-size: 0.65rem; padding: 0.15rem 0.4rem;">${escapeHtml(z.density_level || 'LOW')}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.25rem;">
          <span>Pedestrians: <strong>${z.people_count || 0}</strong></span>
          <span>Cap: <strong>${z.capacity || 20}</strong> (${pct}%)</span>
        </div>
        <div style="width: 100%; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden;">
          <div style="width: ${pct}%; height: 100%; background: ${barColor}; transition: width 0.3s ease;"></div>
        </div>
      </div>
    `;
  }).join('');
}

function updateCongestionTelemetry(c) {
  if (!c) return;

  const teleCongestion = document.getElementById('live-tele-congestion');
  const indexVal = document.getElementById('cong-index-val');
  const indexBar = document.getElementById('cong-index-bar');
  const stationaryEl = document.getElementById('cong-stationary-count');
  const movingEl = document.getElementById('cong-moving-count');
  const bottleneckEl = document.getElementById('cong-bottleneck-zone');
  const badgeEl = document.getElementById('congestion-status-badge');
  const alertBanner = document.getElementById('congestion-alert-banner');
  const alertMsg = document.getElementById('cong-alert-msg');

  const idxPct = Math.round((c.congestion_index || 0) * 100);
  const level = c.congestion_level || 'NORMAL';

  let color = '#10b981';
  let badgeClass = 'badge-online';
  let teleClass = 'telemetry-val-green';

  if (level === 'SEVERE') {
    color = '#ef4444';
    badgeClass = 'badge-critical';
    teleClass = 'telemetry-val-red';
  } else if (level === 'CONGESTED') {
    color = '#f97316';
    badgeClass = 'badge-critical';
    teleClass = 'telemetry-val-amber';
  } else if (level === 'MODERATE') {
    color = '#f59e0b';
    badgeClass = 'badge-warning';
    teleClass = 'telemetry-val-amber';
  }

  if (teleCongestion) {
    teleCongestion.textContent = `${level} (${idxPct}%)`;
    teleCongestion.className = `telemetry-value ${teleClass}`;
  }

  if (indexVal) indexVal.textContent = `${idxPct}%`;
  if (indexBar) {
    indexBar.style.width = `${Math.min(idxPct, 100)}%`;
    indexBar.style.background = color;
  }

  if (stationaryEl) stationaryEl.textContent = c.stationary_count ?? 0;
  if (movingEl) movingEl.textContent = c.moving_count ?? 0;

  if (bottleneckEl) {
    bottleneckEl.textContent = (c.bottleneck_zones && c.bottleneck_zones.length > 0)
      ? c.bottleneck_zones.join(', ')
      : 'None Detected';
  }

  if (badgeEl) {
    badgeEl.textContent = level;
    badgeEl.className = `badge ${badgeClass}`;
  }

  if (alertBanner && alertMsg) {
    if (c.active_alert) {
      alertBanner.style.display = 'block';
      alertMsg.textContent = c.active_alert.message || 'Severe congestion detected!';
    } else {
      alertBanner.style.display = 'none';
    }
  }
}


function toggleStreamPause() {
  const streamImg = document.getElementById('active-live-stream');
  const pauseBtn = document.getElementById('btn-pause-stream');
  if (!streamImg || !activeCameraId) return;

  isPaused = !isPaused;
  if (isPaused) {
    // Unset src to freeze network consumption
    // @ts-ignore
    streamImg.src = '';
    if (pauseBtn) pauseBtn.innerHTML = '<i class="fas fa-play"></i> Resume';
    Toast.info('Video stream paused.');
  } else {
    // Reconnect
    // @ts-ignore
    streamImg.src = getStreamUrl(activeCameraId);
    if (pauseBtn) pauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
    Toast.info('Video stream resumed.');
  }
}

function toggleFullscreen() {
  const container = document.getElementById('live-player-box');
  if (!container) return;

  if (!document.fullscreenElement) {
    container.requestFullscreen().catch(err => {
      Toast.error(`Fullscreen request failed: ${err.message}`);
    });
  } else {
    document.exitFullscreen();
  }
}

function captureSnapshot() {
  const streamImg = document.getElementById('active-live-stream');
  if (!streamImg) return;

  try {
    const canvas = document.createElement('canvas');
    // @ts-ignore
    canvas.width = streamImg.naturalWidth || 640;
    // @ts-ignore
    canvas.height = streamImg.naturalHeight || 360;
    const ctx = canvas.getContext('2d');
    // @ts-ignore
    ctx.drawImage(streamImg, 0, 0);

    const dataUrl = canvas.toDataURL('image/jpeg');
    const link = document.createElement('a');
    link.download = `cctv-snapshot-cam-${activeCameraId}-${Date.now()}.jpg`;
    link.href = dataUrl;
    link.click();
    Toast.success('Surveillance snapshot captured and saved.');
  } catch (err) {
    Toast.error('Snapshot capture restricted by browser security policies.');
  }
}

function showEmptyState() {
  const streamImg = document.getElementById('active-live-stream');
  if (streamImg) streamImg.style.display = 'none';
  const titleEl = document.getElementById('live-stream-title');
  if (titleEl) titleEl.textContent = 'No Surveillance Stream Selected';
}

// @ts-ignore
window.selectLiveCamera = switchCamera;
