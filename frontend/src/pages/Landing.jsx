import { Link } from "react-router-dom";
import { useState } from "react";

export default function Landing() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen text-[#1D1D1F]">
      {/* ================================================================
          HEADER — Glass Nav
          ================================================================ */}
      <header className="glass-nav fixed top-0 left-0 right-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 lg:h-20">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2 sm:gap-3">
              <img
                src="/images/agrotech-blanco.png"
                alt="AgroTech"
                className="h-8 sm:h-10 w-auto"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
              <span className="text-lg sm:text-xl font-bold text-[#1D1D1F]">
                agrotech.
              </span>
            </Link>

            {/* Desktop nav */}
            <nav className="hidden md:flex items-center gap-4 lg:gap-6">
              <a href="#funcionalidades" className="text-sm font-medium text-[#6E6E73] hover:text-[#1D1D1F] transition">
                Funcionalidades
              </a>
              <a href="#planes" className="text-sm font-medium text-[#6E6E73] hover:text-[#1D1D1F] transition">
                Planes
              </a>
              <Link to="/login" className="neuro-button neuro-button-ghost text-sm px-4 py-2">
                Iniciar sesión
              </Link>
              <Link to="/register" className="neuro-button neuro-button-primary text-sm px-5 py-2.5">
                Probar gratis
              </Link>
            </nav>

            {/* Mobile burger */}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-white/50 transition"
              aria-label="Menú"
            >
              <div className="w-5 h-0.5 bg-[#1D1D1F] mb-1 rounded" />
              <div className="w-5 h-0.5 bg-[#1D1D1F] mb-1 rounded" />
              <div className="w-5 h-0.5 bg-[#1D1D1F] rounded" />
            </button>
          </div>

          {/* Mobile menu */}
          {menuOpen && (
            <div className="md:hidden pb-4 border-t border-white/30 pt-3 space-y-3">
              <a href="#funcionalidades" className="block text-sm font-medium text-[#6E6E73] py-2" onClick={() => setMenuOpen(false)}>
                Funcionalidades
              </a>
              <a href="#planes" className="block text-sm font-medium text-[#6E6E73] py-2" onClick={() => setMenuOpen(false)}>
                Planes
              </a>
              <div className="flex flex-col gap-2 pt-2">
                <Link to="/login" className="neuro-button neuro-button-ghost text-sm w-full justify-center">
                  Iniciar sesión
                </Link>
                <Link to="/register" className="neuro-button neuro-button-primary text-sm w-full justify-center">
                  Probar gratis
                </Link>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* ================================================================
          HERO SECTION
          ================================================================ */}
      <section className="relative pt-20 lg:pt-24 pb-16 lg:pb-24 overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#F5F5F7] via-white to-[#E8E8ED]" />
        <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-[#2FB344]/5 to-transparent" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto animate-fade-in-up">
            {/* Badge */}
            <div className="glass-badge mb-6 inline-flex">
              🛰️ Tecnología Satelital Avanzada
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-extrabold leading-[1.1] mb-6">
              Agricultura de Precisión con{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#2FB344] to-[#1E7A2E]">
                Visión Satelital
              </span>
            </h1>

            <p className="text-base sm:text-lg lg:text-xl text-[#6E6E73] leading-relaxed mb-8 max-w-2xl mx-auto">
              Monitorea tus cultivos en tiempo real con análisis satelital avanzado.
              Toma decisiones informadas basadas en datos precisos de NDVI, estrés hídrico
              y pronósticos meteorológicos.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
              <Link to="/register" className="neuro-button neuro-button-primary text-base px-8 py-3.5">
                Acceder a la Plataforma
              </Link>
              <a href="#funcionalidades" className="neuro-button neuro-button-accent text-base px-8 py-3.5">
                Ver funcionalidades
              </a>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
              <div className="stat-card">
                <div className="stat-value text-2xl sm:text-3xl">131.65</div>
                <div className="stat-label">Hectáreas Monitoreadas</div>
              </div>
              <div className="stat-card">
                <div className="stat-value text-2xl sm:text-3xl">12</div>
                <div className="stat-label">Tipos de Cultivo</div>
              </div>
              <div className="stat-card">
                <div className="stat-value text-2xl sm:text-3xl">5 días</div>
                <div className="stat-label">Frecuencia Satelital</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================
          FEATURES SECTION
          ================================================================ */}
      <section id="funcionalidades" className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 lg:mb-16">
            <div className="glass-badge mb-4 inline-flex">🧠 Inteligencia Agrícola</div>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Todo lo que necesitas para tu finca
            </h2>
            <p className="text-[#6E6E73] text-lg max-w-xl mx-auto">
              Deja de adivinar. Toma decisiones basadas en datos satelitales reales.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: "🛰️",
                title: "Índices Satelitales",
                desc: "NDVI, NDMI, SAVI y EVI actualizados cada 5 días desde Sentinel-2. Sin instalar sensores en campo.",
              },
              {
                icon: "🧠",
                title: "Interpretación Agronómica",
                desc: "Cada índice se interpreta según la etapa fenológica de tu cultivo. Un NDVI de 0.45 no significa lo mismo en emergencia que en floración.",
              },
              {
                icon: "⚠️",
                title: "Alertas Inteligentes",
                desc: "Te avisamos cuando detectamos estrés hídrico, pérdida de vigor o anomalías con recomendaciones accionables.",
              },
              {
                icon: "📊",
                title: "Historial Completo",
                desc: "Registro de cada ciclo de cultivo con rendimiento esperado vs real. Aprende de cada cosecha.",
              },
              {
                icon: "🌎",
                title: "Mapa 3D Interactivo",
                desc: "Visualiza tus parcelas en un globo terráqueo 3D con Cesium. Navega, haz zoom y explora.",
              },
              {
                icon: "📱",
                title: "En Cualquier Dispositivo",
                desc: "Funciona en computador, tableta y celular. En el campo o en la oficina.",
              },
            ].map((f) => (
              <div key={f.title} className="glass-card p-6 lg:p-8">
                <div className="text-3xl mb-4">{f.icon}</div>
                <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
                <p className="text-[#6E6E73] text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ================================================================
          PRICING SECTION
          ================================================================ */}
      <section id="planes" className="py-16 lg:py-24 bg-white/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 lg:mb-16">
            <div className="glass-badge mb-4 inline-flex">💰 Planes</div>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Planes para cada agricultor
            </h2>
            <p className="text-[#6E6E73] text-lg">
              Empieza gratis. Crece cuando quieras.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {[
              {
                name: "Explorador",
                price: "Gratis",
                period: "",
                features: [
                  "1 parcela (máx. 30 ha)",
                  "Índice NDVI básico",
                  "10 consultas EOSDA/mes",
                  "Dashboard web",
                ],
                cta: "Comenzar gratis",
                highlight: false,
              },
              {
                name: "Agricultor",
                price: "$79,000",
                period: "COP/mes",
                features: [
                  "Hasta 5 parcelas (150 ha)",
                  "NDVI + NDMI + SAVI",
                  "100 consultas EOSDA/mes",
                  "Alertas agronómicas",
                  "Ciclos de cultivo",
                  "Historial de rendimiento",
                ],
                cta: "Probar 14 días",
                highlight: true,
              },
              {
                name: "Empresarial",
                price: "$179,000",
                period: "COP/mes",
                features: [
                  "Hasta 15 parcelas (300 ha)",
                  "Todos los índices",
                  "300 consultas EOSDA/mes",
                  "Alertas avanzadas",
                  "Hasta 3 usuarios",
                  "Soporte prioritario",
                  "Exportación de reportes",
                ],
                cta: "Probar 14 días",
                highlight: false,
              },
            ].map((plan) => (
              <div
                key={plan.name}
                className={`glass-card p-6 lg:p-8 flex flex-col relative ${
                  plan.highlight ? "glass-card-elevated ring-2 ring-[#2FB344]/30" : ""
                }`}
              >
                {plan.highlight && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-[#2FB344] to-[#1E7A2E] text-white px-5 py-1.5 rounded-full text-xs font-bold shadow-lg">
                    Más popular
                  </div>
                )}
                <h3 className="font-bold text-xl mb-2">{plan.name}</h3>
                <div className="mb-6">
                  <span className="text-3xl lg:text-4xl font-extrabold">{plan.price}</span>
                  {plan.period && (
                    <span className="text-[#86868B] text-sm ml-1">{plan.period}</span>
                  )}
                </div>
                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-[#6E6E73]">
                      <span className="text-[#2FB344] mt-0.5 shrink-0">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to="/register"
                  className={
                    plan.highlight
                      ? "neuro-button neuro-button-primary w-full justify-center"
                      : "neuro-button neuro-button-ghost w-full justify-center"
                  }
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ================================================================
          CTA SECTION
          ================================================================ */}
      <section className="py-20 lg:py-28 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#1E7A2E] to-[#2FB344]" />
        <div className="absolute inset-0 bg-[url('/images/agrotech-blanco.png')] bg-center bg-no-repeat opacity-5 bg-[length:300px]" />
        <div className="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            ¿Listo para ver tu finca desde el espacio?
          </h2>
          <p className="text-white/80 text-lg mb-8 max-w-xl mx-auto">
            Únete a agricultores que ya toman decisiones con datos satelitales.
            Empieza en 2 minutos.
          </p>
          <Link
            to="/register"
            className="inline-flex neuro-button bg-white text-[#1E7A2E] hover:bg-green-50 text-base px-8 py-4 font-bold shadow-xl"
            style={{ borderRadius: 14 }}
          >
            Crear cuenta gratis →
          </Link>
          <p className="text-white/50 text-sm mt-4">
            14 días de prueba · Sin tarjeta de crédito
          </p>
        </div>
      </section>

      {/* ================================================================
          FOOTER
          ================================================================ */}
      <footer className="py-8 border-t border-white/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <img
              src="/images/agrotech-negro.png"
              alt="AgroTech"
              className="h-6 w-auto opacity-60"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
            <span className="text-sm text-[#86868B]">
              © {new Date().getFullYear()} AgroTech Digital · Colombia
            </span>
          </div>
          <div className="flex gap-6 text-sm text-[#86868B]">
            <a href="#" className="hover:text-[#1D1D1F] transition">Términos</a>
            <a href="#" className="hover:text-[#1D1D1F] transition">Privacidad</a>
            <a href="#" className="hover:text-[#1D1D1F] transition">Contacto</a>
          </div>
        </div>
      </footer>
    </div>
  );
}