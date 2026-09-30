/**
 * AI Crowd Management & Public Safety Monitoring System
 * Centralized API Client (Fetch API Wrapper)
 */

import { Toast } from './utils.js';

const API_BASE = '/api';

export class ApiClient {
  static getToken() {
    return localStorage.getItem('crowd_safety_token');
  }

  static setToken(token) {
    localStorage.setItem('crowd_safety_token', token);
  }

  static clearSession() {
    localStorage.removeItem('crowd_safety_token');
    localStorage.removeItem('crowd_safety_user');
  }

  static async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    const token = this.getToken();

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      // Session expired or unauthorized
      if (response.status === 401) {
        if (!window.location.pathname.includes('login.html')) {
          this.clearSession();
          Toast.warning('Your session has expired. Please sign in again.');
          setTimeout(() => {
            window.location.href = 'login.html';
          }, 1000);
        }
        throw new Error('Authentication required.');
      }

      if (!response.ok) {
        let errorMessage = `Request failed (${response.status})`;
        try {
          const errorJson = await response.json();
          if (errorJson.detail) {
            errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
          }
        } catch (_) {}
        throw new Error(errorMessage);
      }

      // Check if response has json body
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      return await response.text();

    } catch (err) {
      // Clean up low-level technical messages for non-technical security operators
      let displayMessage = err.message || 'Unable to communicate with the security server.';
      if (displayMessage.includes('Failed to fetch')) {
        displayMessage = 'Cannot connect to security backend. Please verify that the server is online.';
      }
      throw new Error(displayMessage);
    }
  }

  // HTTP Method Helpers
  static get(endpoint, params = null) {
    let url = endpoint;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null) searchParams.append(key, val);
      });
      const query = searchParams.toString();
      if (query) url += `?${query}`;
    }
    return this.request(url, { method: 'GET' });
  }

  static post(endpoint, body = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  static put(endpoint, body = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body)
    });
  }

  static delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}
