const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function request(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("AgriShield services took too long to respond. Please try again.");
    }
    throw new Error("Unable to connect to AgriShield services. Check that the backend is running and try again.");
  } finally {
    window.clearTimeout(timeout);
  }
}

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
  const response = await request(`${API_BASE}/api/dashboard`, {}, 10000);
  return parseResponse(response);
}

export async function getWeather(latitude, longitude) {
  const params = new URLSearchParams({ latitude, longitude });
  const response = await request(`${API_BASE}/api/weather?${params.toString()}`);
  return parseResponse(response);
}

export async function getMonsoonForecast(location = {}, cropId = "", options = {}) {
  const params = new URLSearchParams();
  if (location?.latitude != null && location?.longitude != null) {
    params.set("latitude", location.latitude);
    params.set("longitude", location.longitude);
  }
  if (cropId) params.set("crop_id", cropId);
  if (location?.location_id) params.set("location_id", location.location_id);
  if (options.horizonDays) params.set("horizon_days", options.horizonDays);
  const response = await request(`${API_BASE}/api/monsoon/forecast?${params.toString()}`, {}, 35000);
  return parseResponse(response);
}

export async function getSavedLocation() {
  return parseResponse(await request(`${API_BASE}/api/location`, {}, 4000));
}

export async function saveLocation(location) {
  return parseResponse(await request(`${API_BASE}/api/location`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(location),
  }));
}

export async function searchLocations(query) {
  return parseResponse(await request(`${API_BASE}/api/location/search?q=${encodeURIComponent(query)}`));
}

export async function reverseGeocode(latitude, longitude) {
  const params = new URLSearchParams({ latitude, longitude });
  return parseResponse(await request(`${API_BASE}/api/location/reverse?${params}`, {}, 12000));
}

export async function getClimateDrivers() {
  return parseResponse(await request(`${API_BASE}/api/climate`, {}, 12000));
}

export async function getSowingDecision(payload) {
  return parseResponse(await request(`${API_BASE}/api/monsoon/sowing-decision`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }, 35000));
}

export async function getCrops() {
  const response = await request(`${API_BASE}/api/crops`);
  return parseResponse(response);
}

export async function getCrop(cropId) {
  const response = await request(`${API_BASE}/api/crops/${cropId}`);
  return parseResponse(response);
}

export async function createCrop(payload) {
  const response = await request(`${API_BASE}/api/crops`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function updateCrop(cropId, payload) {
  return parseResponse(await request(`${API_BASE}/api/crops/${cropId}`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }));
}

export async function archiveCrop(cropId) {
  return parseResponse(await request(`${API_BASE}/api/crops/${cropId}`, { method: "DELETE" }));
}

export async function getModelPerformance(locationId) {
  const params = new URLSearchParams();
  if (locationId) params.set("location_id", locationId);
  return parseResponse(await request(`${API_BASE}/api/monsoon/model-performance?${params}`, {}, 10000));
}

export async function getMonsoonAlerts(location = {}, horizonDays = 14) {
  const params = new URLSearchParams({ horizon_days: String(horizonDays) });
  if (location?.latitude != null && location?.longitude != null) {
    params.set("latitude", location.latitude);
    params.set("longitude", location.longitude);
  }
  if (location?.location_id) params.set("location_id", location.location_id);
  return parseResponse(await request(`${API_BASE}/api/monsoon/alerts?${params}`, {}, 35000));
}

export async function acknowledgeAlert(alertId) {
  return parseResponse(await request(`${API_BASE}/api/monsoon/alerts/${alertId}/acknowledge`, { method: "POST" }));
}

export async function getSowingWindow(location, cropName, cropId) {
  const params = new URLSearchParams({ crop_name: cropName });
  if (location?.latitude != null && location?.longitude != null) {
    params.set("latitude", location.latitude);
    params.set("longitude", location.longitude);
  }
  if (location?.location_id) params.set("location_id", location.location_id);
  if (cropId) params.set("crop_id", cropId);
  return parseResponse(await request(`${API_BASE}/api/monsoon/sowing-window?${params}`, {}, 35000));
}

export async function createTimelineScan(cropId, payload) {
  const response = await request(`${API_BASE}/api/crops/${cropId}/scans`, {
    method: "POST",
    body: uploadForm(payload),
  }, 60000);
  return parseResponse(response);
}

export async function runQuickDiagnosis(payload) {
  const response = await request(`${API_BASE}/api/quick-diagnosis`, {
    method: "POST",
    body: uploadForm(payload),
  }, 60000);
  return parseResponse(response);
}

export async function compareScan(scanId) {
  const response = await request(`${API_BASE}/api/scans/${scanId}/compare`);
  return parseResponse(response);
}
