import { useEffect, useRef, useState } from "react";

let Cesium = null;
let viewerInstance = null;

export default function CesiumViewer({ parcels = [], onParcelSelect, selectedParcelId }) {
  const containerRef = useRef(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);

  // Load Cesium async
  useEffect(() => {
    if (Cesium) {
      initViewer();
      return;
    }

    const script = document.createElement("script");
    script.src = "https://cesium.com/downloads/cesiumjs/releases/1.125/Build/Cesium/Cesium.js";
    script.onload = () => {
      // Cesium is now available globally
      Cesium = window.Cesium;
      // Load CSS
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "https://cesium.com/downloads/cesiumjs/releases/1.125/Build/Cesium/Widgets/widgets.css";
      document.head.appendChild(link);

      // Ion token (free)
      Cesium.Ion.defaultAccessToken =
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJlYWE1OWUxNy1mMWZiLTQzYjYtYTQ0OS1kMWFjYmFkNjc5YzciLCJpZCI6NTc5MzMsImlhdCI6MTYyMjY0NDQwMn0.XcKpgANiY19MC4aXQ2DPuVzFlblCXbBVvZ1oI7syfMg";
      initViewer();
    };
    script.onerror = () => setError("No se pudo cargar el visor 3D de Cesium.");
    document.head.appendChild(script);

    return () => {
      if (viewerInstance) {
        viewerInstance.destroy();
        viewerInstance = null;
        Cesium = null;
        setReady(false);
      }
    };
  }, []);

  const initViewer = () => {
    if (!containerRef.current || viewerInstance) return;

    try {
      viewerInstance = new Cesium.Viewer(containerRef.current, {
        animation: false,
        timeline: false,
        baseLayerPicker: false,
        fullscreenButton: false,
        homeButton: false,
        geocoder: false,
        navigationHelpButton: false,
        sceneModePicker: false,
        infoBox: false,
        selectionIndicator: false,
        shouldAnimate: false,
      });

      // Center on Colombia
      viewerInstance.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(-74.08, 4.61, 1500000),
        orientation: {
          heading: Cesium.Math.toRadians(0),
          pitch: Cesium.Math.toRadians(-60),
          roll: 0,
        },
        duration: 2,
      });

      setReady(true);
    } catch (e) {
      setError(e.message);
    }
  };

  // Draw parcels on map when ready
  useEffect(() => {
    if (!ready || !viewerInstance || !parcels.length) return;

    // Remove existing entities
    viewerInstance.entities.removeAll();

    parcels.forEach((parcel) => {
      if (!parcel.geom || !parcel.geom.coordinates) return;

      const coords = parcel.geom.coordinates[0]; // Polygon ring
      if (!coords || coords.length < 3) return;

      const positions = coords.map(([lon, lat]) =>
        Cesium.Cartesian3.fromDegrees(lon, lat),
      );

      const isSelected = parcel.id === selectedParcelId;
      const color = isSelected
        ? Cesium.Color.fromCssColorString("#16a34a")
        : Cesium.Color.fromCssColorString("#22c55e").withAlpha(0.4);

      const entity = viewerInstance.entities.add({
        name: parcel.name || `Parcela #${parcel.id}`,
        polygon: {
          hierarchy: new Cesium.PolygonHierarchy(positions),
          material: color,
          outline: true,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: isSelected ? 3 : 1,
        },
        label: {
          text: parcel.name || `Parcela #${parcel.id}`,
          font: "14px sans-serif",
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -10),
        },
        description: `<b>${parcel.name || "Parcela"}</b><br/>${parcel.soil_type || ""} ${parcel.topography || ""}`,
      });

      entity.parcelId = parcel.id;
    });

    // Fly to first parcel
    if (parcels.length > 0 && parcels[0].geom?.coordinates?.[0]?.length > 0) {
      const [lon, lat] = parcels[0].geom.coordinates[0][0];
      viewerInstance.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lon, lat, 8000),
        duration: 1.5,
      });
    }
  }, [parcels, selectedParcelId, ready]);

  // Click handler
  useEffect(() => {
    if (!ready || !viewerInstance || !onParcelSelect) return;

    const handler = new Cesium.ScreenSpaceEventHandler(viewerInstance.scene.canvas);
    handler.setInputAction((click) => {
      const picked = viewerInstance.scene.pick(click.position);
      if (Cesium.defined(picked) && picked.id && picked.id.parcelId) {
        onParcelSelect(picked.id.parcelId);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    return () => handler.destroy();
  }, [ready, onParcelSelect]);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center bg-gray-100 rounded-xl">
        <div className="text-center p-8">
          <div className="text-4xl mb-4">🗺️</div>
          <p className="text-red-600 mb-2">{error}</p>
          <p className="text-gray-500 text-sm">
            El mapa satelital estará disponible con conexión a internet.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="h-full w-full rounded-xl overflow-hidden">
      {!ready && (
        <div className="flex h-full items-center justify-center bg-gray-900 text-white">
          <div className="text-center">
            <div className="animate-spin text-4xl mb-4">🛰️</div>
            <p>Cargando visor satelital 3D...</p>
          </div>
        </div>
      )}
    </div>
  );
}