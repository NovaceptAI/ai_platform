// src/utils/auth.js
const AUTH_KEY = 'token';            // keep existing key to avoid breaking
const AUTH_ISSUED = 'authIssuedAt';
const USER_ID_KEY = 'user_id';
const USERNAME_KEY = 'username';
const EXPIRY_MS = 24 * 60 * 60 * 1000; // 24h

export function setAuthToken(token, userId = null, username = null) {
  if (!token) return;
  localStorage.setItem(AUTH_KEY, token);
  localStorage.setItem(AUTH_ISSUED, String(Date.now()));
  if (userId) {
    localStorage.setItem(USER_ID_KEY, userId);
  }
  if (username) {
    localStorage.setItem(USERNAME_KEY, username);
  }
}

export function getAuthToken() {
  const token = localStorage.getItem(AUTH_KEY);
  const issued = parseInt(localStorage.getItem(AUTH_ISSUED) || '0', 10);
  if (!token || !issued) return null;
  if (Date.now() - issued > EXPIRY_MS) {
    clearAuth();
    return null;
  }
  return token;
}

export function getUserId() {
  return localStorage.getItem(USER_ID_KEY);
}

export function getUsername() {
  return localStorage.getItem(USERNAME_KEY);
}

export function clearAuth() {
  localStorage.removeItem(AUTH_KEY);
  localStorage.removeItem(AUTH_ISSUED);
  localStorage.removeItem(USER_ID_KEY);
  localStorage.removeItem(USERNAME_KEY);
}

export function isAuthed() {
  return !!getAuthToken();
}
