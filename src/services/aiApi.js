const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "AgriShield could not complete that request.");
  }
  return payload;
}

function uploadForm(fields) {
  const form = new FormData();
  Object.entries(fields).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      form.append(key, value);
    }
  });
  return form;
}

export function imageUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}

export async function getDashboard() {
  const response = await fetch(`${API_BASE}/api/dashboard`);
  return parseResponse(response);
}

export async function getWeather(latitude, longitude) {
  const params = new URLSearchParams({ latitude, longitude });
  const response = await fetch(`${API_BASE}/api/weather?${params.toString()}`);
  return parseResponse(response);
}

export async function getCrops() {
  const response = await fetch(`${API_BASE}/api/crops`);
  return parseResponse(response);
}

export async function getCrop(cropId) {
  const response = await fetch(`${API_BASE}/api/crops/${cropId}`);
  return parseResponse(response);
}

export async function createCrop(payload) {
  const response = await fetch(`${API_BASE}/api/crops`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function createTimelineScan(cropId, payload) {
  const response = await fetch(`${API_BASE}/api/crops/${cropId}/scans`, {
    method: "POST",
    body: uploadForm(payload),
  });
  return parseResponse(response);
}

export async function runQuickDiagnosis(payload) {
  const response = await fetch(`${API_BASE}/api/quick-diagnosis`, {
    method: "POST",
    body: uploadForm(payload),
  });
  return parseResponse(response);
}

export async function compareScan(scanId) {
  const response = await fetch(`${API_BASE}/api/scans/${scanId}/compare`);
  return parseResponse(response);
}
