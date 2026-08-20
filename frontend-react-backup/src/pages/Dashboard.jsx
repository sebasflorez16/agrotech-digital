import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import CesiumViewer from "../components/Map/CesiumViewer";
import {
  getParcels,
  getParcel,
  getCropHealth,
  getCropCycles,
  getEOSDAScenes,
  interpretIndex,
} from "../api/client";

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [parcels, setParcels] = useState([]);
  const [selectedParcel, setSelectedParcel] = useState(null);
  const [selectedParcelId, setSelectedParcelId] = useState(null);
  const [health, setHealth] = useState(null);
  const [activeCycle, setActiveCycle] = useState(null);
  const [diagnosis, setDiagnosis] = useState(null);
  const [scenes, setScenes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Load parcels
  useEffect(() => {
    (async () => {
      try {
        const { data } = await getParcels();
        const list = Array.isArray(data) ? data : data.results || [];
        setParcels(list);
        if (list.length > 0) setSelectedParcelId(list[0].id);
      } catch {
        setError("No se pudieron cargar tus parcelas.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Load parcel details
  useEffect(() => {
    if (!selectedParcelId) return;
    (async () => {
      try {
        const { data } = await getParcel(selectedParcelId);
        setSelectedParcel(data);

        try {
          const h = await getCropHealth(selectedParcelId);
          setHealth(h.data);
        } catch { setHealth(null); }

        try {
          const { data: cycles } = await getCropCycles({
            parcel_id: selectedParcelId,
            status: "active",
          });
          const cycle = Array.isArray(cycles) ? cycles[0] : cycles?.results?.[0];
          if (cycle) {
            setActiveCycle(cycle);
            if (h?.data?.indices?.ndvi) {
              try {
                const diag = await interpretIndex(cycle.id, "ndvi", h.data.indices.ndvi);
                setDiagnosis(diag.data);
              } catch { setDiagnosis(null); }
            }
          } else {
            setActiveCycle(null);
            setDiagnosis(null);
          }
        } catch { setActiveCycle(null); }

        if (data.eosda_id) {
          try {
            const s = await getEOSDAScenes(data.eosda_id);
            setScenes((s.data?.scenes || []).slice(0, 10));
          } catch { setScenes([]); }
        }
      } catch { setSelectedParcel(null); }
    })();
  }, [selectedParcelId]);

  const handleParcelSelect = useCallback((id) => {
    setSelectedParcelId(id);
    setMobileMenuOpen(false);
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gradient-to-br from-[#F5F5F7] to-[#E8E8ED]">
        <div className="text-center animate-fade-in-up">
          <div className="animate-spin text-6xl mb-4">🛰️</div>
          <p className="text-[#86868B] text-lg">Cargando tu finca...</p>
        </div>
      </div>
    );
  }

  if (error && parcels.length === 0) {
    return (
      <div className="flex h-screen items-center justify-center bg-gradient-to-br from-[#F5F5F7] to-[#E8E8ED] px-4">
        <div className="glass-card p-8 sm:p-12 text-center max-w-md animate-fade-in-up">
          <div className="text-6xl mb-4">🌾</div>
          <h2 className="text-xl font-bold mb-2">Sin parcelas aún</h2>
          <p className="text-[#6E6E73] mb-6">{error}</p>
          <button
            onClick={() => navigate("/onboarding")}
            className="neuro-button neuro-button-primary text-base px-8 py-3 w-full justify-center"
          >
            Crear mi primera parcela
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen text-[#1D1D1F] bg-[#F5F5F7] overflow-hidden">
      {/* ================================================================
          SIDEBAR — Glass Panel (desktop) / Slide-over (mobile)
          ================================================================ */}
      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <aside
        className={`${
          sidebarOpen && !mobileMenuOpen
            ? "hidden lg:flex lg:w-96"
            : mobileMenuOpen
              ? "fixed inset-y-0 left-0 z-50 w-80 flex"
              : "hidden"
        } flex-col border-r border-white/30 glass-nav`}
      >
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-white/20">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <img
                src="/images/agrotech-negro.png"
                alt="AgroTech"
                className="h-7 w-auto"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
              <span className="font-bold text-lg">agrotech.</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => navigate("/onboarding")}
                className="neuro-button neuro-button-primary !text-xs !px-3 !py-1.5"
              >
                + Parcela
              </button>
              <button
                onClick={logout}
                className="text-sm text-[#86868B] hover:text-red-500 transition"
              >
                Salir
              </button>
            </div>
          </div>

          {/* User */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#2FB344] to-[#1E7A2E] flex items-center justify-center text-white font-bold text-sm shadow-md">
              {user?.first_name?.[0] || user?.username?.[0] || "A"}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold truncate">
                {user?.first_name ? `${user.first_name} ${user.last_name || ""}` : user?.username}
              </p>
              <p className="text-xs text-[#86868B]">
                {parcels.length} parcela{parcels.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
        </div>

        {/* Parcel list */}
        <div className="p-4 border-b border-white/20">
          <h3 className="text-xs font-semibold text-[#86868B] uppercase tracking-wider mb-2">
            Mis parcelas
          </h3>
          <div className="space-y-1">
            {parcels.map((p) => (
              <button
                key={p.id}
                onClick={() => handleParcelSelect(p.id)}
                className={`w-full text-left px-3 py-2.5 rounded-xl text-sm transition ${
                  p.id === selectedParcelId
                    ? "bg-white/80 shadow-sm font-semibold text-[#1E7A2E]"
                    : "hover:bg-white/40 text-[#6E6E73]"
                }`}
              >
                📍 {p.name || `Parcela #${p.id}`}
              </button>
            ))}
          </div>
        </div>

        {/* Detail panel */}
        {selectedParcel && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Health */}
            {health?.status && (
              <div className="glass-card p-4">
                <h3 className="text-xs font-semibold text-[#86868B] uppercase tracking-wider mb-3">
                  Estado del cultivo
                </h3>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{health.status.badge?.emoji || "🟡"}</span>
                  <span
                    className="px-3 py-1 rounded-full text-xs font-bold text-white"
                    style={{ backgroundColor: health.status.badge?.color || "#eab308" }}
                  >
                    {health.status.badge?.label || "Sin datos"}
                  </span>
                </div>
                {health.status.message && (
                  <p className="text-sm text-[#6E6E73]">{health.status.message}</p>
                )}
                {health.indices?.ndvi != null && (
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    <div className="bg-white/50 rounded-xl p-3 text-center">
                      <p className="text-xs text-[#86868B]">NDVI</p>
                      <p className="text-xl font-bold text-[#2FB344]">
                        {health.indices.ndvi.toFixed(2)}
                      </p>
                    </div>
                    {health.indices.ndmi != null && (
                      <div className="bg-white/50 rounded-xl p-3 text-center">
                        <p className="text-xs text-[#86868B]">NDMI</p>
                        <p className="text-xl font-bold text-blue-600">
                          {health.indices.ndmi.toFixed(2)}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Active cycle */}
            {activeCycle && (
              <div className="glass-card p-4">
                <h3 className="text-xs font-semibold text-[#86868B] uppercase tracking-wider mb-3">
                  Ciclo activo
                </h3>
                <p className="font-semibold">
                  {activeCycle.crop_catalog_name || activeCycle.crop_name || "Cultivo"}
                </p>
                <p className="text-sm text-[#6E6E73]">
                  Día {activeCycle.days_since_planting} desde siembra
                </p>
                <div className="mt-2 w-full bg-white/50 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-[#2FB344] to-[#4ADE5E] h-2 rounded-full transition-all"
                    style={{ width: `${activeCycle.progress_percent || 0}%` }}
                  />
                </div>
                <p className="text-xs text-[#86868B] mt-1">
                  {activeCycle.progress_percent || 0}% del ciclo
                </p>
                {diagnosis && (
                  <div className={`mt-3 px-3 py-2 rounded-xl text-sm font-medium ${
                    diagnosis.status === "optimal" ? "bg-[#2FB344]/10 text-[#1E7A2E]" :
                    diagnosis.status === "warning" ? "bg-yellow-50 text-yellow-700" :
                    diagnosis.status === "critical" ? "bg-red-50 text-red-700" :
                    "bg-blue-50 text-blue-700"
                  }`}>
                    {diagnosis.message}
                  </div>
                )}
              </div>
            )}

            {/* Parcel info */}
            <div className="glass-card p-4">
              <h3 className="text-xs font-semibold text-[#86868B] uppercase tracking-wider mb-2">
                Información
              </h3>
              <div className="text-sm space-y-1 text-[#6E6E73]">
                {selectedParcel.soil_type && <p>Suelo: <span className="font-medium text-[#1D1D1F]">{selectedParcel.soil_type}</span></p>}
                {selectedParcel.topography && <p>Topografía: <span className="font-medium text-[#1D1D1F]">{selectedParcel.topography}</span></p>}
                <p>Área: <span className="font-medium text-[#1D1D1F]">{selectedParcel.area_hectares?.toFixed(1) || "—"} ha</span></p>
              </div>
            </div>

            {/* Recent scenes */}
            {scenes.length > 0 && (
              <div className="glass-card p-4">
                <h3 className="text-xs font-semibold text-[#86868B] uppercase tracking-wider mb-2">
                  Escenas recientes
                </h3>
                <div className="space-y-1.5">
                  {scenes.slice(0, 5).map((s, i) => (
                    <div key={i} className="flex justify-between text-sm bg-white/40 rounded-lg px-3 py-1.5">
                      <span>{s.date || s.acquisition_date}</span>
                      <span className="text-[#86868B] text-xs">☁️ {s.cloud_cover ?? "—"}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </aside>

      {/* ================================================================
          MAP AREA
          ================================================================ */}
      <main className="flex-1 relative">
        {/* Mobile toggle */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="absolute top-3 left-3 z-30 lg:hidden glass-card p-2 px-3 rounded-xl text-sm font-medium shadow-lg"
        >
          {mobileMenuOpen ? "✕ Cerrar" : "☰ Parcelas"}
        </button>

        <CesiumViewer
          parcels={parcels}
          selectedParcelId={selectedParcelId}
          onParcelSelect={handleParcelSelect}
        />
      </main>
    </div>
  );
}