import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor: attach JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("accessToken");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: auto-refresh on 401
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem("refreshToken");
      if (!refreshToken) {
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${API_BASE}/api/token/refresh/`, {
          refresh: refreshToken,
        });

        localStorage.setItem("accessToken", data.access);
        if (data.refresh) {
          localStorage.setItem("refreshToken", data.refresh);
        }

        processQueue(null, data.access);
        originalRequest.headers.Authorization = `Bearer ${data.access}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

// ── Auth endpoints ─────────────────────────────────────────────
export async function login(username, password) {
  const { data } = await api.post("/api/auth/login/", { username, password });
  // Backend returns tokens nested: data.tokens.access / data.tokens.refresh
  const access = data.tokens?.access || data.access;
  const refresh = data.tokens?.refresh || data.refresh;
  localStorage.setItem("accessToken", access);
  localStorage.setItem("refreshToken", refresh);
  // Fetch user data after login
  if (data.user) {
    localStorage.setItem("userData", JSON.stringify(data.user));
  } else {
    try {
      const me = await api.get("/api/auth/me/");
      localStorage.setItem("userData", JSON.stringify(me.data));
    } catch { /* me endpoint might not be available */ }
  }
  return data;
}

export async function register({ username, email, password, first_name, last_name }) {
  const { data } = await api.post("/api/auth/register/", {
    username,
    email,
    password,
    password2: password,
    first_name,
    last_name,
  });
  return data;
}

export function logout() {
  const refresh = localStorage.getItem("refreshToken");
  if (refresh) {
    api.post("/api/auth/logout/", { refresh }).catch(() => {});
  }
  localStorage.clear();
  window.location.href = "/login";
}

export function isAuthenticated() {
  return !!localStorage.getItem("accessToken");
}

// ── Parcels ────────────────────────────────────────────────────
export function getParcels() {
  return api.get("/api/parcels/parcel/");
}

export function getParcel(id) {
  return api.get(`/api/parcels/parcel/${id}/`);
}

export function createParcel(geom, name, options = {}) {
  return api.post("/api/parcels/parcel/", {
    geom,
    name,
    description: options.description || "",
    soil_type: options.soil_type || "",
    topography: options.topography || "",
    ...options,
  });
}

// ── Crop Catalog ───────────────────────────────────────────────
export function getCropCatalog() {
  return api.get("/api/crop/catalog/");
}

export function getCropCatalogDetail(id) {
  return api.get(`/api/crop/catalog/${id}/`);
}

// ── Crop Cycles ────────────────────────────────────────────────
export function getCropCycles(params = {}) {
  return api.get("/api/crop/cycles/", { params });
}

export function createCropCycle(data) {
  return api.post("/api/crop/cycles/", data);
}

export function interpretIndex(cycleId, indexType, value) {
  return api.post(`/api/crop/cycles/${cycleId}/interpret/`, {
    index_type: indexType,
    value,
  });
}

// ── Crop Health ────────────────────────────────────────────────
export function getCropHealth(parcelId) {
  return api.get(`/api/parcels/parcel/${parcelId}/health/`);
}

// ── EOSDA ──────────────────────────────────────────────────────
export function getEOSDAScenes(fieldId) {
  return api.post("/api/parcels/eosda-scenes/", { field_id: fieldId });
}

export function getEOSDAImage(fieldId, indexType, sceneDate) {
  return api.post("/api/parcels/eosda-image/", {
    field_id: fieldId,
    index_type: indexType,
    date: sceneDate,
  });
}

// ── Billing / Plans ────────────────────────────────────────────
export function getPlans() {
  return api.get("/billing/api/plans/");
}

// ── Onboarding Wizard ──────────────────────────────────────────
export function completeOnboarding(data) {
  return api.post("/api/parcels/onboarding/", data);
}

export default api;