/**
 * AI Crowd Management & Public Safety Monitoring System
 * Settings Page Controller
 */

import { ApiClient } from './api.js';
import { AuthService } from './auth.js';
import { Toast } from './utils.js';

export async function initSettings() {
  const user = await AuthService.verifySession();
  if (!user) return;

  setupForm();
  await loadSettings();
}

async function loadSettings() {
  try {
    const settings = await ApiClient.get('/settings');
    populateSettingsForm(settings);
  } catch (err) {
    console.error('Failed to load settings:', err);
    Toast.error('Could not fetch security thresholds.');
  }
}

function populateSettingsForm(data) {
  const fields = [
    'crowd_warning_threshold',
    'crowd_critical_threshold',
    'high_density_threshold',
    'congestion_movement_threshold',
    'congestion_duration_seconds',
    'fire_confidence_threshold',
    'smoke_confidence_threshold',
    'suspicious_object_confidence',
    'abandoned_object_duration_seconds'
  ];

  fields.forEach(field => {
    const el = document.getElementById(field);
    if (el && data[field] !== undefined) {
      // @ts-ignore
      el.value = data[field];
    }
  });
}

function setupForm() {
  const form = document.getElementById('settings-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const payload = {
      // @ts-ignore
      crowd_warning_threshold: parseInt(document.getElementById('crowd_warning_threshold').value) || 30,
      // @ts-ignore
      crowd_critical_threshold: parseInt(document.getElementById('crowd_critical_threshold').value) || 50,
      // @ts-ignore
      high_density_threshold: parseFloat(document.getElementById('high_density_threshold').value) || 0.75,
      // @ts-ignore
      congestion_movement_threshold: parseFloat(document.getElementById('congestion_movement_threshold').value) || 0.5,
      // @ts-ignore
      congestion_duration_seconds: parseInt(document.getElementById('congestion_duration_seconds').value) || 15,
      // @ts-ignore
      fire_confidence_threshold: parseFloat(document.getElementById('fire_confidence_threshold').value) || 0.65,
      // @ts-ignore
      smoke_confidence_threshold: parseFloat(document.getElementById('smoke_confidence_threshold').value) || 0.6,
      // @ts-ignore
      suspicious_object_confidence: parseFloat(document.getElementById('suspicious_object_confidence').value) || 0.7,
      // @ts-ignore
      abandoned_object_duration_seconds: parseInt(document.getElementById('abandoned_object_duration_seconds').value) || 60
    };

    try {
      await ApiClient.put('/settings', payload);
      Toast.success('Surveillance safety thresholds updated successfully.');
    } catch (err) {
      Toast.error(err.message);
    }
  });
}
