/**
 * AI Crowd Management & Public Safety Monitoring System
 * Authentication & Session Management Module
 */

import { ApiClient } from './api.js';
import { Toast } from './utils.js';

export class AuthService {
  static getCurrentUser() {
    try {
      const stored = localStorage.getItem('crowd_safety_user');
      return stored ? JSON.parse(stored) : null;
    } catch (_) {
      return null;
    }
  }

  static setCurrentUser(user) {
    localStorage.setItem('crowd_safety_user', JSON.stringify(user));
  }

  static isAuthenticated() {
    return !!ApiClient.getToken();
  }

  static async login(email, password) {
    const data = await ApiClient.post('/auth/login', { email, password });
    ApiClient.setToken(data.access_token);
    this.setCurrentUser({
      id: data.user_id,
      username: data.username,
      email: data.email,
      role: data.role
    });
    return data;
  }

  static logout() {
    ApiClient.clearSession();
    window.location.href = 'login.html';
  }

  static async verifySession() {
    if (!this.isAuthenticated()) {
      window.location.href = 'login.html';
      return null;
    }

    try {
      const me = await ApiClient.get('/auth/me');
      this.setCurrentUser(me);
      this.populateUserInterface(me);
      return me;
    } catch (err) {
      console.warn('Session verification error:', err);
      this.logout();
      return null;
    }
  }

  static populateUserInterface(user) {
    if (!user) return;
    
    // Update sidebar profile name and badge
    const nameEl = document.getElementById('current-user-name');
    const roleEl = document.getElementById('current-user-role');
    const avatarEl = document.getElementById('current-user-avatar');

    if (nameEl) nameEl.textContent = user.full_name || user.username;
    if (roleEl) roleEl.textContent = user.role.replace('_', ' ');
    if (avatarEl) avatarEl.textContent = (user.username || 'U').charAt(0).toUpperCase();

    // Role-based visibility for Admin-only items
    const adminElements = document.querySelectorAll('.admin-only');
    if (user.role !== 'ADMIN') {
      adminElements.forEach(el => {
        el.style.display = 'none';
      });
    }
  }
}
