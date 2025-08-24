// src/utils/auth.js
const AUTH_KEY = 'token';            // keep existing key to avoid breaking
const AUTH_ISSUED = 'authIssuedAt';
const EXPIRY_MS = 24 * 60 * 60 * 1000; // 24h

export function setAuthToken(token) {
  if (!token) return;
  localStorage.setItem(AUTH_KEY, token);
  localStorage.setItem(AUTH_ISSUED, String(Date.now()));
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

export function clearAuth() {
  localStorage.removeItem(AUTH_KEY);
  localStorage.removeItem(AUTH_ISSUED);
}

export function isAuthed() {
  return !!getAuthToken();
}
