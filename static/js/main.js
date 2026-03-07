/**
 * main.js — Movie Tracker
 *
 * Handles:
 *  - Radarr modal open/close + folder dropdown population
 *  - POST to /radarr/movies/{tmdb_id}/add and per-card button state updates
 *  - Manual TMDb refresh trigger (header "Refresh Now" button)
 *  - Filter navigation via URLSearchParams (no duplicate params)
 */

"use strict";

// ─── State ───────────────────────────────────────────────────────────────────

let currentTmdbId = null;
let currentTitle = null;

// ─── Filter navigation ───────────────────────────────────────────────────────

/**
 * Navigate to /movies with all current form filter values merged with a
 * single key override.  Uses URLSearchParams so every param appears exactly
 * once and values are properly encoded.
 *
 * @param {string} key    Query param name to set (e.g. "region")
 * @param {string} value  New value — pass "" to clear that filter
 */
function navigateWithFilter(key, value) {
  const form = document.getElementById("filter-form");
  const params = new URLSearchParams();

  // Collect every named form control that has a non-empty value
  const fields = ["genre", "release_type", "provider", "sort"];
  fields.forEach((field) => {
    const el = form ? form.elements[field] : null;
    const v = el ? el.value : "";
    if (v) params.set(field, v);
  });

  // Apply the override
  if (value) {
    params.set(key, value);
  } else {
    params.delete(key);
  }

  window.location.href = "/movies?" + params.toString();
}

// ─── Modal ────────────────────────────────────────────────────────────────────

/**
 * Open the "Add to Radarr" modal for a specific movie.
 * Reads tmdb_id and title from data attributes on the button or its
 * nearest ancestor article element — avoids injecting untrusted text
 * into inline JS.
 * @param {HTMLElement} btn  The button element that was clicked
 */
function openModal(btn) {
  const article = btn.closest("article[data-tmdb-id]") || btn;
  currentTmdbId = parseInt(article.dataset.tmdbId, 10);
  currentTitle = article.dataset.title || "";

  document.getElementById("modal-movie-title").textContent = currentTitle;
  document.getElementById("radarr-modal").classList.remove("hidden");
  document.body.style.overflow = "hidden";

  loadFolders();
}

function closeModal() {
  document.getElementById("radarr-modal").classList.add("hidden");
  document.body.style.overflow = "";
  currentTmdbId = null;
  currentTitle = null;
}

// Close on Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

// ─── Folder dropdown ─────────────────────────────────────────────────────────

async function loadFolders() {
  const select = document.getElementById("folder-select");
  const confirmBtn = document.getElementById("modal-confirm-btn");

  select.innerHTML = '<option value="">Loading…</option>';
  confirmBtn.disabled = true;

  try {
    const res = await fetch("/radarr/folders");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (!data.folders || data.folders.length === 0) {
      select.innerHTML = '<option value="">No folders found in Radarr</option>';
      return;
    }

    select.innerHTML = data.folders
      .map(
        (f) =>
          `<option value="${escapeAttr(f.path)}">${escapeHtml(f.label)}</option>`
      )
      .join("");

    confirmBtn.disabled = false;
  } catch (err) {
    select.innerHTML = `<option value="">Error loading folders: ${escapeHtml(err.message)}</option>`;
    console.error("[Radarr] loadFolders error:", err);
  }
}

// ─── Add to Radarr ────────────────────────────────────────────────────────────

async function confirmAddToRadarr() {
  if (!currentTmdbId) return;

  const folderPath = document.getElementById("folder-select").value;
  if (!folderPath) return;

  const confirmBtn = document.getElementById("modal-confirm-btn");
  confirmBtn.disabled = true;
  confirmBtn.textContent = "Adding…";

  try {
    const res = await fetch(`/radarr/movies/${currentTmdbId}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_path: folderPath }),
    });

    const data = await res.json();
    closeModal();
    updateCardButton(currentTmdbId, data);
  } catch (err) {
    console.error("[Radarr] confirmAddToRadarr error:", err);
    closeModal();
    updateCardButton(currentTmdbId, {
      success: false,
      already_exists: false,
      message: "Network error — please retry.",
    });
  }
}

/**
 * Update the "Add to Radarr" button on the movie card based on the API result.
 * @param {number} tmdbId
 * @param {{ success: boolean, already_exists: boolean, message: string }} result
 */
function updateCardButton(tmdbId, result) {
  // There can be multiple buttons with the same tmdb_id (grid + detail page)
  const buttons = document.querySelectorAll(`#radarr-btn-${tmdbId}`);
  buttons.forEach((btn) => {
    btn.disabled = true;
    btn.onclick = null;

    if (result.already_exists) {
      btn.textContent = "Already in Radarr";
      btn.className = btn.className
        .replace(/bg-\S+/g, "")
        .replace(/border-\S+/g, "")
        .replace(/text-\S+/g, "")
        .trim();
      btn.classList.add(
        "bg-gray-800", "border", "border-gray-700",
        "text-gray-500", "cursor-default"
      );
    } else if (result.success) {
      btn.textContent = "Added ✓";
      btn.className = btn.className
        .replace(/bg-\S+/g, "")
        .replace(/border-\S+/g, "")
        .replace(/text-\S+/g, "")
        .trim();
      btn.classList.add(
        "bg-green-700/20", "border", "border-green-700/40",
        "text-green-400", "cursor-default"
      );
    } else {
      // Error — allow retry
      btn.disabled = false;
      btn.textContent = "Error — retry?";
      btn.className = btn.className
        .replace(/bg-\S+/g, "")
        .replace(/border-\S+/g, "")
        .replace(/text-\S+/g, "")
        .trim();
      btn.classList.add(
        "bg-red-700/20", "border", "border-red-700/40", "text-red-400"
      );
      btn.onclick = () => openModal(btn);
    }
  });
}

// ─── Manual refresh ───────────────────────────────────────────────────────────

async function triggerFetch() {
  const btn = document.getElementById("refresh-btn");
  const label = document.getElementById("refresh-label");
  const icon = document.getElementById("refresh-icon");

  if (!btn) return;

  label.textContent = "Fetching…";
  btn.disabled = true;
  icon.classList.add("animate-spin");

  try {
    const res = await fetch("/admin/fetch", { method: "POST" });
    if (res.ok) {
      label.textContent = "Fetch started!";
    } else {
      label.textContent = "Error";
    }
  } catch {
    label.textContent = "Error";
  }

  // Reset button after 3 seconds
  setTimeout(() => {
    label.textContent = "Refresh Now";
    btn.disabled = false;
    icon.classList.remove("animate-spin");
  }, 3000);
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(str) {
  return String(str).replace(/"/g, "&quot;");
}


// ─── State ───────────────────────────────────────────────────────────────────

let currentTmdbId = null;
let currentTitle = null;

// ─── Modal ────────────────────────────────────────────────────────────────────

/**
 * Open the "Add to Radarr" modal for a specific movie.
 * Reads tmdb_id and title from data attributes on the button or its
 * nearest ancestor article element — avoids injecting untrusted text
 * into inline JS.
 * @param {HTMLElement} btn  The button element that was clicked
 */
function openModal(btn) {
  const article = btn.closest("article[data-tmdb-id]") || btn;
  currentTmdbId = parseInt(article.dataset.tmdbId, 10);
  currentTitle = article.dataset.title || "";

  document.getElementById("modal-movie-title").textContent = currentTitle;
  document.getElementById("radarr-modal").classList.remove("hidden");
  document.body.style.overflow = "hidden";

  loadFolders();
}

function closeModal() {
  document.getElementById("radarr-modal").classList.add("hidden");
  document.body.style.overflow = "";
  currentTmdbId = null;
  currentTitle = null;
}

// Close on Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

// ─── Folder dropdown ─────────────────────────────────────────────────────────

async function loadFolders() {
  const select = document.getElementById("folder-select");
  const confirmBtn = document.getElementById("modal-confirm-btn");

  select.innerHTML = '<option value="">Loading…</option>';
  confirmBtn.disabled = true;

  try {
    const res = await fetch("/radarr/folders");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (!data.folders || data.folders.length === 0) {
      select.innerHTML = '<option value="">No folders found in Radarr</option>';
      return;
    }

    select.innerHTML = data.folders
      .map(
        (f) =>
          `<option value="${escapeAttr(f.path)}">${escapeHtml(f.label)}</option>`
      )
      .join("");

    confirmBtn.disabled = false;
  } catch (err) {
    select.innerHTML = `<option value="">Error loading folders: ${escapeHtml(err.message)}</option>`;
    console.error("[Radarr] loadFolders error:", err);
  }
}

// ─── Add to Radarr ────────────────────────────────────────────────────────────

async function confirmAddToRadarr() {
  if (!currentTmdbId) return;

  const folderPath = document.getElementById("folder-select").value;
  if (!folderPath) return;

  const confirmBtn = document.getElementById("modal-confirm-btn");
  confirmBtn.disabled = true;
  confirmBtn.textContent = "Adding…";

  try {
    const res = await fetch(`/radarr/movies/${currentTmdbId}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_path: folderPath }),
    });

    const data = await res.json();
    closeModal();
    updateCardButton(currentTmdbId, data);
  } catch (err) {
    console.error("[Radarr] confirmAddToRadarr error:", err);
    closeModal();
    updateCardButton(currentTmdbId, {
      success: false,
      already_exists: false,
      message: "Network error — please retry.",
    });
  }
}

/**
 * Update the "Add to Radarr" button on the movie card based on the API result.
 * @param {number} tmdbId
 * @param {{ success: boolean, already_exists: boolean, message: string }} result
 */
function updateCardButton(tmdbId, result) {
  // There can be multiple buttons with the same tmdb_id (grid + detail page)
  const buttons = document.querySelectorAll(`#radarr-btn-${tmdbId}`);
  buttons.forEach((btn) => {
    btn.disabled = true;
    btn.onclick = null;

    if (result.already_exists) {
      btn.textContent = "Already in Radarr";
      btn.className = btn.className
        .replace(/bg-\S+/g, "")
        .replace(/border-\S+/g, "")
        .replace(/text-\S+/g, "")
        .trim();
      btn.classList.add(
        "bg-gray-800", "border", "border-gray-700",
        "text-gray-500", "cursor-default"
      );
    } else if (result.success) {
      btn.textContent = "Added ✓";
      btn.className = btn.className
        .replace(/bg-\S+/g, "")
        .replace(/border-\S+/g, "")
        .replace(/text-\S+/g, "")
        .trim();
      btn.classList.add(
        "bg-green-700/20", "border", "border-green-700/40",
        "text-green-400", "cursor-default"
      );
    } else {
      // Error — allow retry
      btn.disabled = false;
      btn.textContent = "Error — retry?";
      btn.className = btn.className
        .replace(/bg-\S+/g, "")
        .replace(/border-\S+/g, "")
        .replace(/text-\S+/g, "")
        .trim();
      btn.classList.add(
        "bg-red-700/20", "border", "border-red-700/40", "text-red-400"
      );
      btn.onclick = () => openModal(btn);
    }
  });
}

// ─── Manual refresh ───────────────────────────────────────────────────────────

async function triggerFetch() {
  const btn = document.getElementById("refresh-btn");
  const label = document.getElementById("refresh-label");
  const icon = document.getElementById("refresh-icon");

  if (!btn) return;

  label.textContent = "Fetching…";
  btn.disabled = true;
  icon.classList.add("animate-spin");

  try {
    const res = await fetch("/admin/fetch", { method: "POST" });
    if (res.ok) {
      label.textContent = "Fetch started!";
    } else {
      label.textContent = "Error";
    }
  } catch {
    label.textContent = "Error";
  }

  // Reset button after 3 seconds
  setTimeout(() => {
    label.textContent = "Refresh Now";
    btn.disabled = false;
    icon.classList.remove("animate-spin");
  }, 3000);
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(str) {
  return String(str).replace(/"/g, "&quot;");
}
