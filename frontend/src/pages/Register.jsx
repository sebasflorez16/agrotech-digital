import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Register() {
  const { register } = useAuth();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    username: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (form.password !== form.confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    if (form.password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    setLoading(true);
    try {
      await register({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        username: form.username,
        password: form.password,
      });
      window.location.href = "/login?registered=true";
    } catch (err) {
      const data = err.response?.data;
      if (data) {
        const messages = [];
        if (typeof data === "string") messages.push(data);
        else {
          Object.entries(data).forEach(([key, val]) => {
            messages.push(`${key}: ${Array.isArray(val) ? val.join(", ") : val}`);
          });
        }
        setError(messages.join("\n"));
      } else {
        setError("Error al registrarse. Intenta de nuevo.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row text-[#1D1D1F]">
      {/* ================================================================
          LEFT: Brand (hidden on mobile)
          ================================================================ */}
      <div className="hidden lg:flex lg:w-5/12 xl:w-1/2 bg-gradient-to-br from-[#1E7A2E] via-[#2FB344] to-[#4ADE5E] items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute bottom-20 left-20 w-80 h-80 rounded-full bg-white blur-3xl" />
          <div className="absolute top-10 right-10 w-64 h-64 rounded-full bg-white blur-3xl" />
        </div>

        <div className="relative text-white max-w-md">
          <div className="flex items-center gap-3 mb-8">
            <img src="/images/agrotech-blanco.png" alt="AgroTech" className="h-10 w-auto" />
            <span className="text-2xl font-bold">agrotech.</span>
          </div>
          <div className="text-7xl mb-8">🌱</div>
          <h1 className="text-4xl font-bold mb-6 leading-tight">
            Comienza a monitorear tus cultivos hoy
          </h1>
          <p className="text-lg text-white/80 leading-relaxed">
            Sin tarjetas de crédito. Sin compromisos. Solo datos satelitales que te ayudan a cultivar mejor.
          </p>
          <div className="mt-10 space-y-3">
            {[
              "✅ 14 días de prueba gratis",
              "✅ Sin tarjeta de crédito",
              "✅ Cancela cuando quieras",
            ].map((item) => (
              <div key={item} className="text-white/80 text-base">{item}</div>
            ))}
          </div>
        </div>
      </div>

      {/* ================================================================
          RIGHT: Register Form
          ================================================================ */}
      <div className="flex flex-1 items-center justify-center px-4 sm:px-6 py-8 lg:py-10 bg-gradient-to-br from-[#F5F5F7] to-white">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-6">
            <img
              src="/images/agrotech-negro.png"
              alt="AgroTech"
              className="h-8 mx-auto mb-2"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
            <h1 className="text-xl font-bold">AgroTech Digital</h1>
          </div>

          <div className="glass-card p-5 sm:p-8 lg:p-10">
            <h2 className="text-xl sm:text-2xl font-bold mb-1">Crear cuenta gratis</h2>
            <p className="text-[#86868B] text-sm mb-6">
              ¿Ya tienes cuenta?{" "}
              <Link to="/login" className="text-[#2FB344] font-medium hover:underline">
                Inicia sesión
              </Link>
            </p>

            {error && (
              <div className="alert-badge alert-badge-danger mb-6 w-full text-sm whitespace-pre-line">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-[#6E6E73] mb-1">Nombre</label>
                  <input
                    type="text"
                    required
                    value={form.first_name}
                    onChange={update("first_name")}
                    className="glass-input text-sm py-2.5"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#6E6E73] mb-1">Apellido</label>
                  <input
                    type="text"
                    required
                    value={form.last_name}
                    onChange={update("last_name")}
                    className="glass-input text-sm py-2.5"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#6E6E73] mb-1">Correo electrónico</label>
                <input
                  type="email"
                  autoComplete="email"
                  required
                  value={form.email}
                  onChange={update("email")}
                  className="glass-input text-sm py-2.5"
                  placeholder="tu@correo.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#6E6E73] mb-1">Nombre de usuario</label>
                <input
                  type="text"
                  autoComplete="username"
                  required
                  value={form.username}
                  onChange={update("username")}
                  className="glass-input text-sm py-2.5"
                  placeholder="juan_agricultor"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#6E6E73] mb-1">Contraseña</label>
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={form.password}
                  onChange={update("password")}
                  className="glass-input text-sm py-2.5"
                  placeholder="Mínimo 8 caracteres"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#6E6E73] mb-1">Confirmar contraseña</label>
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  value={form.confirmPassword}
                  onChange={update("confirmPassword")}
                  className="glass-input text-sm py-2.5"
                  placeholder="Repite la contraseña"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="neuro-button neuro-button-primary w-full justify-center text-base py-3 mt-2 disabled:opacity-50"
              >
                {loading ? "Creando cuenta..." : "Crear cuenta gratis"}
              </button>
            </form>

            <p className="text-xs text-[#86868B] text-center mt-4">
              Al registrarte aceptas nuestros términos y condiciones.
            </p>

            <div className="mt-4 pt-3 border-t border-white/30 text-center">
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