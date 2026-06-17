import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getCropCatalog, createParcel, createCropCycle } from "../api/client";

const STEPS = [
  { id: "location", icon: "📍", title: "¿Dónde está tu finca?", subtitle: "Dibuja el polígono de tu parcela en el mapa" },
  { id: "crop", icon: "🌱", title: "¿Qué cultivas?", subtitle: "Selecciona el cultivo de tu parcela" },
  { id: "processing", icon: "🛰️", title: "Analizando tu campo", subtitle: "Conectando con satélites Sentinel-2..." },
  { id: "result", icon: "✨", title: "¡Tu cultivo desde el espacio!", subtitle: "Ya puedes ver el NDVI de tu parcela" },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [crops, setCrops] = useState([]);
  const [selectedCrop, setSelectedCrop] = useState(null);
  const [parcelName, setParcelName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mapPoints, setMapPoints] = useState([]);
  const mapRef = useRef(null);

  // Load crop catalog
  useEffect(() => {
    (async () => {
      try {
        const { data } = await getCropCatalog();
        const list = Array.isArray(data) ? data : data.results || [];
        setCrops(list);
        if (list.length > 0) setSelectedCrop(list[0].id);
      } catch { setError("No se pudo cargar el catálogo de cultivos."); }
    })();
  }, []);

  // Initialize Leaflet map for step 0
  useEffect(() => {
    if (step !== 0 || !mapRef.current) return;

    const loadLeaflet = () => {
      if (window._onboardingMap) {
        window._onboardingMap.invalidateSize();
        return;
      }
      if (!window.L) return setTimeout(loadLeaflet, 200);

      const L = window.L;
      const map = L.map(mapRef.current, {
        zoomControl: false,
        attributionControl: false,
      }).setView([4.61, -74.08], 6);
      window._onboardingMap = map;

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
      }).addTo(map);

      // Geolocation
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => map.setView([pos.coords.latitude, pos.coords.longitude], 15),
          () => {}
        );
      }

      const drawnItems = new L.FeatureGroup();
      map.addLayer(drawnItems);

      const drawControl = new L.Control.Draw({
        edit: { featureGroup: drawnItems },
        draw: {
          polygon: { allowIntersection: false, showArea: true, shapeOptions: { color: "#2FB344", weight: 2 } },
          polyline: false, rectangle: true, circle: false, marker: false, circlemarker: false,
        },
      });
      map.addControl(drawControl);

      map.on(L.Draw.Event.CREATED, (e) => {
        drawnItems.clearLayers();
        const layer = e.layerType === "rectangle" ? e.layer.toGeoJSON().geometry.coordinates[0] : e.layer.getLatLngs()[0];
        const coords = Array.isArray(layer[0])
          ? layer.map((ll) => [ll.lng, ll.lat])
          : layer.map((ll) => [ll.lng, ll.lat]);
        coords.push(coords[0]); // Close ring
        setMapPoints(coords);
        drawnItems.addLayer(e.layer);
      });
    };

    // Load Leaflet CSS + JS
    if (!document.getElementById("leaflet-css")) {
      const link = document.createElement("link");
      link.id = "leaflet-css";
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      document.head.appendChild(link);
    }
    if (!document.getElementById("leaflet-draw-css")) {
      const dc = document.createElement("link");
      dc.id = "leaflet-draw-css";
      dc.rel = "stylesheet";
      dc.href = "https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.css";
      document.head.appendChild(dc);
    }

    if (!window.L) {
      const script = document.createElement("script");
      script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
      script.onload = () => {
        const ds = document.createElement("script");
        ds.src = "https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.js";
        ds.onload = loadLeaflet;
        document.head.appendChild(ds);
      };
      document.head.appendChild(script);
    } else {
      loadLeaflet();
    }

    return () => {
      if (window._onboardingMap) {
        window._onboardingMap.remove();
        window._onboardingMap = null;
      }
    };
  }, [step]);

  const handleCreateParcel = async () => {
    if (mapPoints.length < 3) {
      setError("Dibuja un polígono en el mapa antes de continuar.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const geom = { type: "Polygon", coordinates: [mapPoints] };
      const { data } = await createParcel(geom, parcelName || "Mi Parcela");
      setStep(2);

      // Attach crop cycle
      if (selectedCrop) {
        try {
          await createCropCycle({
            parcel: data.id,
            crop_catalog: selectedCrop,
            planting_date: new Date().toISOString().split("T")[0],
            status: "active",
          });
        } catch { /* optional */ }
      }

      setTimeout(() => setStep(3), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || "Error al crear la parcela.");
    } finally {
      setLoading(false);
    }
  };

  const finish = () => navigate("/dashboard");

  const cropEmoji = (category) => {
    const map = { cereals: "🌽", legumes: "🫘", fruits: "🍊", tubers: "🥔", industrial: "☕", forage: "🌿", oilseeds: "🌻" };
    return map[category] || "🌱";
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row text-[#1D1D1F] bg-[#F5F5F7]">
      {/* ================================================================
          LEFT: Stepper (desktop sidebar / mobile top nav)
          ================================================================ */}
      <aside className="lg:w-72 xl:w-80 glass-nav border-b lg:border-b-0 lg:border-r border-white/30 p-4 lg:p-6 flex lg:flex-col">
        <div className="flex items-center gap-2 mb-6 shrink-0">
          <img
            src="/images/agrotech-negro.png"
            alt="AgroTech"
            className="h-7 w-auto"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
          <span className="font-bold text-lg">agrotech.</span>
        </div>

        {/* Stepper — horizontal on mobile, vertical on desktop */}
        <nav className="flex lg:flex-col gap-2 lg:gap-1 overflow-x-auto lg:overflow-visible pb-2 lg:pb-0">
          {STEPS.map((s, i) => (
            <div
              key={s.id}
              className={`flex items-center gap-2 lg:gap-3 px-3 py-2 lg:py-2.5 rounded-xl text-xs lg:text-sm whitespace-nowrap lg:whitespace-normal shrink-0 transition ${
                i === step
                  ? "bg-white/80 shadow-sm font-semibold text-[#1E7A2E]"
                  : i < step
                    ? "text-[#2FB344]"
                    : "text-[#86868B]"
              }`}
            >
              <span className="text-base lg:text-lg">{i < step ? "✅" : s.icon}</span>
              <span className="hidden sm:inline">{s.title}</span>
            </div>
          ))}
        </nav>

        <div className="hidden lg:block mt-auto pt-4 border-t border-white/20">
          <p className="text-xs text-[#86868B]">⏱️ ~2 minutos</p>
          <p className="text-xs text-[#86868B]">Sin tarjeta de crédito</p>
        </div>
      </aside>

      {/* ================================================================
          RIGHT: Step Content
          ================================================================ */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Step header */}
        <div className="p-4 sm:p-6 lg:p-8 pb-2 lg:pb-4">
          <p className="text-xs sm:text-sm text-[#86868B] mb-1">
            Paso {step + 1} de {STEPS.length}
          </p>
          <h2 className="text-xl sm:text-2xl font-bold">{STEPS[step].title}</h2>
          <p className="text-[#6E6E73] text-sm mt-1">{STEPS[step].subtitle}</p>
        </div>

        {/* Error */}
        {error && (
          <div className="mx-4 sm:mx-6 lg:mx-8 mb-3 alert-badge alert-badge-danger text-sm">
            {error}
          </div>
        )}

        {/* STEP 0: Draw polygon */}
        {step === 0 && (
          <div className="flex-1 mx-3 sm:mx-5 lg:mx-8 mb-4 sm:mb-6 bg-white/30 rounded-2xl overflow-hidden border border-white/40 relative shadow-inner">
            <div ref={mapRef} className="h-full w-full" />
            {/* Overlay controls */}
            <div className="absolute bottom-3 left-3 right-3 z-[1000] flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                value={parcelName}
                onChange={(e) => setParcelName(e.target.value)}
                placeholder="Nombre de tu parcela (ej: Lote Norte)"
                className="flex-1 glass-input text-sm py-2.5 !bg-white/80 shadow-lg"
              />
              <button
                onClick={handleCreateParcel}
                disabled={loading || mapPoints.length < 3}
                className="neuro-button neuro-button-primary text-sm px-6 py-2.5 shadow-lg disabled:opacity-50 shrink-0"
              >
                {loading ? "Creando..." : "Continuar →"}
              </button>
            </div>
            {mapPoints.length < 3 && (
              <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] dark-glass px-3 py-1.5 text-xs sm:text-sm whitespace-nowrap">
                🖱️ Dibuja tu parcela con las herramientas del mapa
              </div>
            )}
          </div>
        )}

        {/* STEP 1: Select crop */}
        {step === 1 && (
          <div className="flex-1 mx-3 sm:mx-5 lg:mx-8 mb-4 sm:mb-6 overflow-auto">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
              {crops.map((crop) => (
                <button
                  key={crop.id}
                  onClick={() => setSelectedCrop(crop.id)}
                  className={`glass-card p-3 sm:p-4 text-left transition ${
                    selectedCrop === crop.id
                      ? "ring-2 ring-[#2FB344] glass-card-elevated"
                      : ""
                  }`}
                >
                  <div className="text-2xl sm:text-3xl mb-2">{cropEmoji(crop.category)}</div>
                  <p className="font-semibold text-sm">{crop.name}</p>
                  <p className="text-xs text-[#86868B] mt-0.5">
                    {crop.cycle_days_min}–{crop.cycle_days_max} días
                  </p>
                </button>
              ))}
            </div>
            <div className="mt-6 flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => setStep(0)}
                className="neuro-button neuro-button-ghost text-sm px-6 py-2.5 w-full sm:w-auto justify-center"
              >
                ← Atrás
              </button>
              <button
                onClick={handleCreateParcel}
                disabled={loading || !selectedCrop}
                className="neuro-button neuro-button-primary text-sm px-6 py-2.5 w-full sm:w-auto justify-center disabled:opacity-50"
              >
                {loading ? "Creando..." : "Analizar mi campo →"}
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: Processing */}
        {step === 2 && (
          <div className="flex-1 flex items-center justify-center px-4">
            <div className="glass-card p-8 sm:p-12 text-center max-w-md animate-fade-in-up">
              <div className="animate-spin text-6xl mb-6">🛰️</div>
              <h3 className="text-xl font-bold mb-2">Analizando tu campo</h3>
              <p className="text-[#6E6E73] mb-6">
                Estamos obteniendo imágenes del satélite Sentinel-2 para calcular los índices vegetativos de tu cultivo.
              </p>
              <div className="w-full bg-white/50 rounded-full h-2 overflow-hidden">
                <div className="bg-gradient-to-r from-[#2FB344] to-[#4ADE5E] h-2 rounded-full animate-pulse w-2/3" />
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Result */}
        {step === 3 && (
          <div className="flex-1 flex items-center justify-center px-4">
            <div className="text-center max-w-lg animate-fade-in-up">
              <div className="text-6xl mb-6">🎉</div>
              <h3 className="text-xl sm:text-2xl font-bold mb-2">
                ¡{parcelName || "Tu parcela"} está siendo monitoreada!
              </h3>
              <p className="text-[#6E6E73] mb-8 max-w-md mx-auto">
                Los satélites capturarán nuevas imágenes cada 5 días. Te avisaremos cuando detectemos cambios importantes en tu cultivo.
              </p>

              <div className="grid grid-cols-3 gap-3 sm:gap-4 mb-8">
                {[
                  { icon: "🛰️", title: "Monitoreo", sub: "Cada 5 días" },
                  { icon: "⚠️", title: "Alertas", sub: "Notificaciones" },
                  { icon: "📊", title: "Reportes", sub: "Histórico NDVI" },
                ].map((item) => (
                  <div key={item.title} className="glass-card p-3 sm:p-4 text-center">
                    <div className="text-xl sm:text-2xl mb-1">{item.icon}</div>
                    <p className="text-xs sm:text-sm font-semibold">{item.title}</p>
                    <p className="text-[10px] sm:text-xs text-[#86868B]">{item.sub}</p>
                  </div>
                ))}
              </div>

              <button
                onClick={finish}
                className="neuro-button neuro-button-primary text-base px-8 py-3.5 w-full sm:w-auto shadow-lg"
              >
                Ir a mi dashboard →
              </button>

              <p className="mt-4 text-sm text-[#86868B]">
                ¿Otra parcela?{" "}
                <button onClick={() => { setStep(0); setMapPoints([]); }} className="text-[#2FB344] font-medium hover:underline">
                  Agregar otra
                </button>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}