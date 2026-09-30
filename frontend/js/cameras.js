/**
 * AI Crowd Management & Public Safety Monitoring System
 * Camera Management Page Controller
 */

import { ApiClient } from './api.js';
import { AuthService } from './auth.js';
import { Toast, escapeHtml, formatDate } from './utils.js';

let allCameras = [];
let editingCameraId = null;

export async function initCameras() {
  const user = await AuthService.verifySession();
  if (!user) return;

  setupEventListeners();
  await loadCameras();
}

function setupEventListeners() {
  // Add Camera Button
  const addBtn = document.getElementById('btn-add-camera');
  if (addBtn) {
    addBtn.addEventListener('click', () => openCameraModal());
  }

  // Search input
  const searchInput = document.getElementById('camera-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      // @ts-ignore
      filterCameras(e.target.value);
    });
  }

  // Dynamic Type Selection inside Modal
  const inputTypeSelect = document.getElementById('camera-input-type');
  if (inputTypeSelect) {
    inputTypeSelect.addEventListener('change', (e) => {
      // @ts-ignore
      updateDynamicFields(e.target.value);
    });
  }

  // Camera Form Submit
  const form = document.getElementById('camera-form');
  if (form) {
    form.addEventListener('submit', handleFormSubmit);
  }

  // Modal Test Connection Button
  const testBtn = document.getElementById('btn-test-candidate');
  if (testBtn) {
    testBtn.addEventListener('click', handleCandidateTest);
  }

  // Close modal buttons
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', closeCameraModal);
  });
}

export async function loadCameras() {
  try {
    const cameras = await ApiClient.get('/cameras');
    allCameras = cameras;
    renderCameras(allCameras);
  } catch (err) {
    console.error('Failed to load cameras:', err);
    Toast.error('Could not load camera registry.');
  }
}

function filterCameras(query) {
  const q = (query || '').toLowerCase().trim();
  if (!q) {
    renderCameras(allCameras);
    return;
  }
  const filtered = allCameras.filter(c => 
    c.name.toLowerCase().includes(q) || 
    c.location.toLowerCase().includes(q) ||
    c.input_type.toLowerCase().includes(q)
  );
  renderCameras(filtered);
}

function renderCameras(cameras) {
  const grid = document.getElementById('cameras-grid');
  const countBadge = document.getElementById('camera-count-badge');
  if (countBadge) countBadge.textContent = `${cameras.length} Nodes`;
  if (!grid) return;

  if (cameras.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 2rem; background: var(--bg-glass-card); border-radius: var(--radius-lg); border: 1px dashed var(--border-subtle);">
        <i class="fas fa-video-slash" style="font-size: 2.5rem; color: var(--text-muted); margin-bottom: 1rem; display: block;"></i>
        <h3 style="margin-bottom: 0.5rem;">No Surveillance Cameras Registered</h3>
        <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.5rem;">Add your first camera node (Video file, USB Webcam, or RTSP stream) to start monitoring.</p>
        <button class="btn btn-primary" onclick="window.openCameraModal()">
          <i class="fas fa-plus"></i> Add Surveillance Node
        </button>
      </div>
    `;
    return;
  }

  grid.innerHTML = cameras.map(c => {
    let statusClass = 'badge-offline';
    if (c.status === 'ONLINE') statusClass = 'badge-online';
    if (c.status === 'ERROR') statusClass = 'badge-critical';
    if (c.status === 'DISABLED') statusClass = 'badge-offline';

    let typeTagClass = 'type-tag-file';
    let typeIcon = 'fa-file-video';
    if (c.input_type === 'WEBCAM') {
      typeTagClass = 'type-tag-webcam';
      typeIcon = 'fa-camera';
    } else if (c.input_type === 'RTSP') {
      typeTagClass = 'type-tag-rtsp';
      typeIcon = 'fa-network-wired';
    }

    const streamUrl = `/api/cameras/${c.id}/stream`;

    return `
      <div class="card camera-card">
        <div class="camera-card-top">
          <img src="${streamUrl}" class="camera-preview-thumb" alt="${escapeHtml(c.name)}" onerror="this.src='/static/assets/icons/camera-placeholder.svg'" loading="lazy" />
          <div class="camera-card-badges">
            <span class="type-tag ${typeTagClass}">
              <i class="fas ${typeIcon}"></i> ${c.input_type}
            </span>
            <span class="badge ${statusClass}">
              ${c.status}
            </span>
          </div>
        </div>

        <div class="camera-card-body">
          <h3 class="camera-name">${escapeHtml(c.name)}</h3>
          <div class="camera-location">
            <i class="fas fa-map-marker-alt"></i> ${escapeHtml(c.location)}
          </div>

          <div class="camera-meta-list">
            <div class="camera-meta-item">
              <span>Resolution</span>
              <strong>${c.resolution || '640x360'}</strong>
            </div>
            <div class="camera-meta-item">
              <span>Frame Rate</span>
              <strong>${c.fps ? c.fps + ' FPS' : 'N/A'}</strong>
            </div>
            <div class="camera-meta-item" style="grid-column: span 2;">
              <span>Source Endpoint</span>
              <strong style="font-family: var(--font-mono); font-size: 0.7rem; word-break: break-all;">
                ${escapeHtml(c.source)}
              </strong>
            </div>
          </div>

          <div class="camera-card-actions">
            <div>
              <button class="btn btn-sm btn-secondary" onclick="window.testCamera(${c.id})" title="Test Connection">
                <i class="fas fa-plug"></i> Test
              </button>
              <button class="btn btn-sm ${c.enabled ? 'btn-secondary' : 'btn-primary'}" onclick="window.toggleCameraStatus(${c.id}, ${!c.enabled})" title="${c.enabled ? 'Disable' : 'Enable'}">
                <i class="fas ${c.enabled ? 'fa-power-off' : 'fa-check'}"></i> ${c.enabled ? 'Disable' : 'Enable'}
              </button>
            </div>
            <div>
              <a href="live-monitoring.html?camera_id=${c.id}" class="btn btn-sm btn-primary" title="View Live Console">
                <i class="fas fa-eye"></i> Live
              </a>
              <button class="btn btn-sm btn-secondary admin-only" onclick="window.editCamera(${c.id})" title="Edit Configuration">
                <i class="fas fa-edit"></i>
              </button>
              <button class="btn btn-sm btn-danger admin-only" onclick="window.deleteCamera(${c.id}, '${escapeHtml(c.name)}')" title="Delete Camera">
                <i class="fas fa-trash-alt"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

export function openCameraModal(camera = null) {
  const modal = document.getElementById('camera-modal');
  const title = document.getElementById('modal-title');
  const form = document.getElementById('camera-form');
  const testOutput = document.getElementById('candidate-test-result');
  if (testOutput) testOutput.style.display = 'none';

  if (!modal || !form) return;

  editingCameraId = camera ? camera.id : null;
  if (title) title.textContent = camera ? 'Edit Surveillance Camera' : 'Register Surveillance Node';

  // Populate fields
  // @ts-ignore
  document.getElementById('camera-name').value = camera ? camera.name : '';
  // @ts-ignore
  document.getElementById('camera-location').value = camera ? camera.location : '';
  // @ts-ignore
  document.getElementById('camera-input-type').value = camera ? camera.input_type : 'VIDEO_FILE';
  // @ts-ignore
  document.getElementById('camera-source').value = camera ? camera.source : '';
  // @ts-ignore
  document.getElementById('camera-username').value = camera ? (camera.username || '') : '';
  // @ts-ignore
  document.getElementById('camera-password').value = '';
  // @ts-ignore
  document.getElementById('camera-description').value = camera ? (camera.description || '') : '';

  updateDynamicFields(camera ? camera.input_type : 'VIDEO_FILE');
  modal.classList.add('open');
}

export function closeCameraModal() {
  const modal = document.getElementById('camera-modal');
  if (modal) modal.classList.remove('open');
  editingCameraId = null;
}

function updateDynamicFields(type) {
  const sourceLabel = document.getElementById('source-label');
  const sourceHelp = document.getElementById('source-help');
  const rtspCredsSection = document.getElementById('rtsp-credentials-group');
  const sampleBtn = document.getElementById('btn-use-sample-video');

  if (type === 'VIDEO_FILE') {
    if (sourceLabel) sourceLabel.textContent = 'Video File Path (MP4)';
    if (sourceHelp) sourceHelp.textContent = 'Enter absolute path to an MP4 video or use our pre-packaged crowd video.';
    if (rtspCredsSection) rtspCredsSection.style.display = 'none';
    if (sampleBtn) sampleBtn.style.display = 'inline-block';
  } else if (type === 'WEBCAM') {
    if (sourceLabel) sourceLabel.textContent = 'Webcam Device Index';
    if (sourceHelp) sourceHelp.textContent = 'Enter 0 for built-in laptop webcam, or 1 for external USB camera.';
    if (rtspCredsSection) rtspCredsSection.style.display = 'none';
    if (sampleBtn) sampleBtn.style.display = 'none';
    const srcInput = document.getElementById('camera-source');
    if (srcInput && (!srcInput.value || srcInput.value.includes('.mp4') || srcInput.value.includes('rtsp://'))) {
      srcInput.value = '0';
    }
  } else if (type === 'RTSP') {
    if (sourceLabel) sourceLabel.textContent = 'Complete RTSP CCTV URL';
    if (sourceHelp) sourceHelp.textContent = 'e.g. rtsp://192.168.1.100:554/live/ch0 or enter credentials below.';
    if (rtspCredsSection) rtspCredsSection.style.display = 'grid';
    if (sampleBtn) sampleBtn.style.display = 'none';
  }
}

async function handleFormSubmit(e) {
  e.preventDefault();
  // @ts-ignore
  const name = document.getElementById('camera-name').value.trim();
  // @ts-ignore
  const location = document.getElementById('camera-location').value.trim();
  // @ts-ignore
  const input_type = document.getElementById('camera-input-type').value;
  // @ts-ignore
  const source = document.getElementById('camera-source').value.trim();
  // @ts-ignore
  const username = document.getElementById('camera-username').value.trim() || null;
  // @ts-ignore
  const password = document.getElementById('camera-password').value || null;
  // @ts-ignore
  const description = document.getElementById('camera-description').value.trim() || null;

  if (!name || !location || !source) {
    Toast.error('Please complete all mandatory camera fields.');
    return;
  }

  const payload = {
    name,
    location,
    input_type,
    source,
    username,
    password,
    description
  };

  try {
    if (editingCameraId) {
      await ApiClient.put(`/cameras/${editingCameraId}`, payload);
      Toast.success(`Camera '${name}' updated successfully.`);
    } else {
      await ApiClient.post('/cameras', payload);
      Toast.success(`Camera '${name}' registered successfully.`);
    }
    closeCameraModal();
    await loadCameras();
  } catch (err) {
    Toast.error(err.message);
  }
}

async function handleCandidateTest() {
  // @ts-ignore
  const input_type = document.getElementById('camera-input-type').value;
  // @ts-ignore
  const source = document.getElementById('camera-source').value.trim();
  // @ts-ignore
  const username = document.getElementById('camera-username').value.trim() || null;
  // @ts-ignore
  const password = document.getElementById('camera-password').value || null;

  if (!source) {
    Toast.warning('Please enter a source endpoint to test.');
    return;
  }

  const resultBox = document.getElementById('candidate-test-result');
  if (resultBox) {
    resultBox.style.display = 'block';
    resultBox.innerHTML = '<span class="spinner"></span> Testing source connection...';
    resultBox.className = 'credentials-demo-box';
  }

  try {
    const res = await ApiClient.post('/cameras/test-raw', {
      input_type,
      source,
      username,
      password
    });

    if (resultBox) {
      if (res.success) {
        resultBox.style.borderColor = 'var(--status-online)';
        resultBox.innerHTML = `
          <strong style="color: var(--status-online);"><i class="fas fa-check-circle"></i> ${res.message}</strong><br>
          Resolution: ${res.details?.resolution || 'N/A'} | FPS: ${res.details?.fps || 'N/A'} | Latency: ${res.details?.latency_ms}ms
        `;
      } else {
        resultBox.style.borderColor = 'var(--status-critical)';
        resultBox.innerHTML = `
          <strong style="color: var(--status-critical);"><i class="fas fa-exclamation-triangle"></i> Connection Failed</strong><br>
          ${res.message}<br>
          <small style="color: var(--text-muted);">Please check network routing, RTSP credentials, or device index.</small>
        `;
      }
    }
  } catch (err) {
    if (resultBox) {
      resultBox.style.borderColor = 'var(--status-critical)';
      resultBox.innerHTML = `<strong style="color: var(--status-critical);">${err.message}</strong>`;
    }
  }
}

// Global window actions for inline buttons
// @ts-ignore
window.openCameraModal = openCameraModal;
// @ts-ignore
window.testCamera = async function(id) {
  Toast.info('Testing camera connection...');
  try {
    const res = await ApiClient.post(`/cameras/${id}/test`);
    if (res.success) {
      Toast.success(`Camera Online: ${res.details?.resolution} @ ${res.details?.fps} FPS`);
    } else {
      Toast.error(`Camera Offline: ${res.message}`);
    }
    await loadCameras();
  } catch (err) {
    Toast.error(err.message);
  }
};

// @ts-ignore
window.toggleCameraStatus = async function(id, enable) {
  try {
    if (enable) {
      await ApiClient.post(`/cameras/${id}/enable`);
      Toast.success('Camera enabled.');
    } else {
      await ApiClient.post(`/cameras/${id}/disable`);
      Toast.info('Camera disabled.');
    }
    await loadCameras();
  } catch (err) {
    Toast.error(err.message);
  }
};

// @ts-ignore
window.editCamera = function(id) {
  const camera = allCameras.find(c => c.id === id);
  if (camera) openCameraModal(camera);
};

// @ts-ignore
window.deleteCamera = async function(id, name) {
  if (confirm(`Are you sure you want to delete surveillance camera '${name}'?`)) {
    try {
      await ApiClient.delete(`/cameras/${id}`);
      Toast.success(`Camera '${name}' deleted.`);
      await loadCameras();
    } catch (err) {
      Toast.error(err.message);
    }
  }
};

// @ts-ignore
window.setSampleVideoPath = function() {
  // @ts-ignore
  const sourceInput = document.getElementById('camera-source');
  if (sourceInput) {
    // Relative or server absolute path to sample crowd
    sourceInput.value = 'frontend/assets/samples/sample_crowd.mp4';
    Toast.info('Loaded pre-packaged sample video path.');
  }
};
