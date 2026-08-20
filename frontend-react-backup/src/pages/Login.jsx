import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      window.location.href = "/dashboard";
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        "Error al iniciar sesión. Revisa tus credenciales.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row text-[#1D1D1F]">
      {/* ================================================================
          LEFT: Hero / Brand (hidden on mobile, visible on lg+)
          ================================================================ */}
      <div className="hidden lg:flex lg:w-5/12 xl:w-1/2 bg-gradient-to-br from-[#1E7A2E] via-[#2FB344] to-[#4ADE5E] items-center justify-center p-12 relative overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-10 w-64 h-64 rounded-full bg-white blur-3xl" />
          <div className="absolute bottom-10 right-10 w-96 h-96 rounded-full bg-white blur-3xl" />
        </div>

        <div className="relative text-white max-w-md">
          <div className="flex items-center gap-3 mb-8">
            <img
              src="/images/agrotech-blanco.png"
              alt="AgroTech"
              className="h-10 w-auto"
            />
            <span className="text-2xl font-bold">agrotech.</span>
          </div>
          <div className="text-7xl mb-8">🌾</div>
          <h1 className="text-4xl font-bold mb-6 leading-tight">
            Tus cultivos monitoreados desde el espacio
          </h1>
          <p className="text-lg text-white/80 leading-relaxed">
            NDVI, NDMI, SAVI y alertas agronómicas en tiempo real
            para tomar decisiones inteligentes en tu finca.
          </p>
          <div className="mt-10 grid grid-cols-3 gap-4">
            {[
              { icon: "🛰️", label: "Satelital" },
              { icon: "📊", label: "Analítica" },
              { icon: "⚠️", label: "Alertas" },
            ].map((item) => (
              <div
                key={item.label}
                className="bg-white/10 backdrop-blur rounded-xl p-4 text-center border border-white/10"
              >
                <div className="text-2xl mb-1">{item.icon}</div>
                <div className="text-xs font-medium text-white/80">{item.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ================================================================
          RIGHT: Login Form
          ================================================================ */}
      <div className="flex flex-1 items-center justify-center px-4 sm:px-6 py-10 lg:py-12 bg-gradient-to-br from-[#F5F5F7] to-white">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-8">
            <img
              src="/images/agrotech-negro.png"
              alt="AgroTech"
              className="h-10 mx-auto mb-3"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
            <h1 className="text-2xl font-bold">AgroTech Digital</h1>
          </div>

          <div className="glass-card p-6 sm:p-8 lg:p-10">
            <h2 className="text-xl sm:text-2xl font-bold mb-1">Iniciar sesión</h2>
            <p className="text-[#86868B] text-sm mb-6">
              ¿No tienes cuenta?{" "}
              <Link to="/register" className="text-[#2FB344] font-medium hover:underline">
                Regístrate gratis
              </Link>
            </p>

            {error && (
              <div className="alert-badge alert-badge-danger mb-6 w-full text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-[#6E6E73] mb-1.5">
                  Usuario o correo
                </label>
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="glass-input"
                  placeholder="tu@correo.com"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-[#6E6E73] mb-1.5">
                  Contraseña
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="glass-input"
                  placeholder="••••••••"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="neuro-button neuro-button-primary w-full justify-center text-base py-3 mt-2 disabled:opacity-50"
              >
                {loading ? "Iniciando sesión..." : "Ingresar"}
              </button>
            </form>

            <div className="mt-6 pt-4 border-t border-white/30 text-center">
              <Link to="/" className="text-sm text-[#86868B] hover:text-[#2FB344] transition">
                ← Volver al inicio
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}