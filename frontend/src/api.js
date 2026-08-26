/**
 * api.js — Centralized API base URL configuration.
 *
 * In production (Vercel), VITE_API_BASE_URL is set to the Render backend URL.
 * In local development, the Vite dev server proxy handles /api/* and /health
 * transparently, so an empty string is correct (relative paths work as-is).
 *
 * Usage:
 *   import { API_BASE, apiFetch } from '../api';
 *   const res = await apiFetch('/api/$expand?q=jvara');
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Drop-in replacement for fetch() that automatically prepends API_BASE.
 * Preserves all original fetch() options (method, headers, body, etc.).
 *
 * @param {string} path  - Must start with '/' e.g. '/api/history'
 * @param {RequestInit} [options]
 * @returns {Promise<Response>}
 */
export function apiFetch(path, options) {
  return fetch(`${API_BASE}${path}`, options);
}
