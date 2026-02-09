"""Script para crear register.html en el frontend."""

REGISTER_HTML = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crear Cuenta - AgroTech Digital</title>
    <link rel="shortcut icon" href="../../images/agrotech solo negro.png">
    <link rel="stylesheet" href="../../css/liquid-glass-system.css">
    <script src="../../js/config.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/@tabler/icons-webfont@latest/tabler-icons.min.css" />
    <style>
        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #F5F5F7 0%, #E8E8ED 100%);
            background-attachment: fixed;
            position: relative;
            overflow-x: hidden;
        }
        .bg-blob {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.3;
            animation: float 20s infinite ease-in-out;
        }
        .blob-1 {
            width: 400px; height: 400px;
            background: linear-gradient(135deg, var(--agrotech-primary) 0%, var(--agrotech-primary-light) 100%);
            top: -200px; left: -200px;
        }
        .blob-2 {
            width: 300px; height: 300px;
            background: linear-gradient(135deg, var(--agrotech-accent) 0%, #FFB340 100%);
            bottom: -150px; right: -150px;
            animation-delay: 5s;
        }
        .blob-3 {
            width: 250px; height: 250px;
            background: linear-gradient(135deg, #34C759 0%, #30D158 100%);
            top: 50%; right: -100px;
            animation-delay: 10s;
        }
        @keyframes float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            25% { transform: translate(30px, -30px) scale(1.1); }
            50% { transform: translate(-20px, 20px) scale(0.9); }
            75% { transform: translate(20px, 10px) scale(1.05); }
        }
        .register-container {
            background: var(--glass-white);
            backdrop-filter: var(--glass-blur);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-xl);
            padding: var(--space-2xl);
            width: 90%; max-width: 520px;
            box-shadow: var(--shadow-glass);
            position: relative; z-index: 10;
            margin: 2rem 0;
        }
        .logo-container { text-align: center; margin-bottom: var(--space-xl); }
        .logo-container img {
            max-width: 80px; margin-bottom: var(--space-sm);
            filter: drop-shadow(0 4px 12px rgba(0,0,0,0.1));
        }
        .brand-name {
            font-size: 1.5rem; font-weight: var(--font-weight-bold);
            background: linear-gradient(135deg, var(--agrotech-primary) 0%, var(--agrotech-primary-dark) 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text; margin-bottom: var(--space-xs);
        }
        .subtitle { color: var(--text-secondary); font-size: 0.875rem; }
        .steps { display: flex; justify-content: center; gap: var(--space-md); margin-bottom: var(--space-xl); align-items: center; }
        .step { display: flex; align-items: center; gap: var(--space-xs); font-size: 0.8rem; color: var(--text-tertiary); transition: all 0.3s ease; }
        .step.active { color: var(--agrotech-primary); font-weight: var(--font-weight-semibold); }
        .step.completed { color: var(--agrotech-primary-dark); }
        .step-dot {
            width: 28px; height: 28px; border-radius: 50%;
            border: 2px solid var(--glass-border);
            display: flex; align-items: center; justify-content: center;
            font-size: 0.75rem; font-weight: var(--font-weight-bold);
            transition: all 0.3s ease;
        }
        .step.active .step-dot { background: var(--agrotech-primary); border-color: var(--agrotech-primary); color: white; }
        .step.completed .step-dot { background: var(--agrotech-primary-dark); border-color: var(--agrotech-primary-dark); color: white; }
        .step-line { width: 40px; height: 2px; background: var(--glass-border); transition: background 0.3s ease; }
        .step-line.active { background: var(--agrotech-primary); }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); }
        .form-group { margin-bottom: var(--space-md); }
        .form-label { display: block; font-size: 0.8rem; font-weight: var(--font-weight-medium); color: var(--text-primary); margin-bottom: 4px; }
        .input-wrapper { position: relative; }
        .input-icon { position: absolute; left: var(--space-md); top: 50%; transform: translateY(-50%); color: var(--text-tertiary); font-size: 1.15rem; }
        .form-input {
            width: 100%; padding: 0.7rem 0.7rem 0.7rem 2.75rem;
            background: var(--glass-white); backdrop-filter: var(--glass-blur-light);
            border: 1px solid var(--glass-border); border-radius: var(--radius-md);
            font-family: var(--font-primary); font-size: 0.95rem;
            color: var(--text-primary); transition: all 0.2s ease;
            box-sizing: border-box;
        }
        .form-input:focus { outline: none; border-color: var(--agrotech-primary); box-shadow: 0 0 0 3px rgba(47,179,68,0.1); background: rgba(255,255,255,0.95); }
        .form-input.error { border-color: #DC2626; box-shadow: 0 0 0 3px rgba(220,38,38,0.1); }
        .field-error { color: #DC2626; font-size: 0.75rem; margin-top: 2px; display: none; }
        .field-error.show { display: block; }
        .password-strength { height: 3px; border-radius: 2px; background: var(--glass-dark); margin-top: 6px; overflow: hidden; }
        .password-strength-bar { height: 100%; border-radius: 2px; transition: all 0.3s ease; width: 0%; }
        .strength-weak { background: #DC2626; width: 33% !important; }
        .strength-medium { background: #F59E0B; width: 66% !important; }
        .strength-strong { background: #16A34A; width: 100% !important; }
        .btn-register {
            width: 100%; padding: 0.8rem var(--space-xl);
            background: linear-gradient(135deg, var(--agrotech-primary) 0%, var(--agrotech-primary-dark) 100%);
            color: white; border: none; border-radius: var(--radius-full);
            font-weight: var(--font-weight-semibold); font-size: 1rem;
            cursor: pointer; transition: all 0.3s ease;
            box-shadow: 0 8px 24px rgba(47,179,68,0.3); margin-top: var(--space-md);
        }
        .btn-register:hover { background: linear-gradient(135deg, var(--agrotech-primary-light) 0%, var(--agrotech-primary) 100%); transform: translateY(-2px); box-shadow: 0 12px 32px rgba(47,179,68,0.4); }
        .btn-register:active { transform: translateY(0); }
        .btn-register:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .error-message {
            background: rgba(255,59,48,0.1); border: 1px solid rgba(255,59,48,0.2);
            border-radius: var(--radius-md); padding: var(--space-sm) var(--space-md);
            margin-bottom: var(--space-md); color: #DC2626; font-size: 0.8rem; display: none;
        }
        .error-message.show { display: flex; align-items: center; gap: var(--space-sm); }
        .success-message {
            background: rgba(22,163,74,0.1); border: 1px solid rgba(22,163,74,0.2);
            border-radius: var(--radius-md); padding: var(--space-lg);
            text-align: center; color: #16A34A; display: none;
        }
        .success-message.show { display: block; }
        .success-message h3 { margin: 0 0 var(--space-sm); font-size: 1.1rem; }
        .loading-spinner {
            display: none; width: 20px; height: 20px;
            border: 2px solid rgba(255,255,255,0.3); border-top-color: white;
            border-radius: 50%; animation: spin 0.6s linear infinite;
            margin-right: var(--space-sm);
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .btn-register.loading .loading-spinner { display: inline-block; }
        .login-link { text-align: center; margin-top: var(--space-lg); font-size: 0.875rem; color: var(--text-secondary); }
        .login-link a { color: var(--agrotech-primary); text-decoration: none; font-weight: var(--font-weight-semibold); transition: color 0.2s ease; }
        .login-link a:hover { color: var(--agrotech-primary-dark); }
        .btn-back {
            background: var(--glass-white) !important; color: var(--text-primary) !important;
            box-shadow: var(--shadow-sm) !important; border: 1px solid var(--glass-border) !important;
            flex: 0 0 auto !important; width: auto !important; padding: 0.8rem 1.5rem !important;
        }
        .btn-back:hover { background: rgba(255,255,255,0.9) !important; transform: translateY(-1px); }
        @media (max-width: 600px) {
            .register-container { padding: var(--space-xl) var(--space-lg); border-radius: var(--radius-lg); }
            .form-row { grid-template-columns: 1fr; }
            .brand-name { font-size: 1.3rem; }
            .steps { gap: var(--space-sm); }
            .step-line { width: 24px; }
        }
    </style>
</head>
<body>
    <div class="bg-blob blob-1"></div>
    <div class="bg-blob blob-2"></div>
    <div class="bg-blob blob-3"></div>

    <div class="register-container">
        <div class="logo-container">
            <img src="../../images/agrotech solo negro.png" alt="AgroTech">
            <div class="brand-name">AgroTech Digital</div>
            <p class="subtitle">Crea tu cuenta y empieza tu prueba gratuita de 14 dias</p>
        </div>

        <div class="steps">
            <div class="step active" id="step1">
                <span class="step-dot">1</span>
                <span>Tu cuenta</span>
            </div>
            <div class="step-line" id="stepLine1"></div>
            <div class="step" id="step2">
                <span class="step-dot">2</span>
                <span>Tu finca</span>
            </div>
        </div>

        <div id="errorMessage" class="error-message">
            <i class="ti ti-alert-circle"></i>
            <span id="errorText"></span>
        </div>

        <div id="successMessage" class="success-message">
            <h3>&#127881; Cuenta creada exitosamente!</h3>
            <p>Redirigiendo al dashboard...</p>
        </div>

        <form id="registerForm">
            <!-- Step 1: Account -->
            <div id="formStep1">
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label" for="name">Nombre</label>
                        <div class="input-wrapper">
                            <i class="ti ti-user input-icon"></i>
                            <input type="text" id="name" class="form-input" placeholder="Juan" required autocomplete="given-name">
                        </div>
                        <span class="field-error" id="nameError"></span>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="last_name">Apellido</label>
                        <div class="input-wrapper">
                            <i class="ti ti-user input-icon"></i>
                            <input type="text" id="last_name" class="form-input" placeholder="Perez" required autocomplete="family-name">
                        </div>
                        <span class="field-error" id="lastNameError"></span>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label" for="email">Correo electronico</label>
                    <div class="input-wrapper">
                        <i class="ti ti-mail input-icon"></i>
                        <input type="email" id="email" class="form-input" placeholder="juan@email.com" required autocomplete="email">
                    </div>
                    <span class="field-error" id="emailError"></span>
                </div>

                <div class="form-group">
                    <label class="form-label" for="username">Usuario</label>
                    <div class="input-wrapper">
                        <i class="ti ti-at input-icon"></i>
                        <input type="text" id="username" class="form-input" placeholder="juanperez" required autocomplete="username">
                    </div>
                    <span class="field-error" id="usernameError"></span>
                </div>

                <div class="form-group">
                    <label class="form-label" for="password">Contrasena</label>
                    <div class="input-wrapper">
                        <i class="ti ti-lock input-icon"></i>
                        <input type="password" id="password" class="form-input" placeholder="Minimo 8 caracteres" required autocomplete="new-password">
                    </div>
                    <div class="password-strength">
                        <div class="password-strength-bar" id="strengthBar"></div>
                    </div>
                    <span class="field-error" id="passwordError"></span>
                </div>

                <div class="form-group">
                    <label class="form-label" for="password_confirm">Confirmar contrasena</label>
                    <div class="input-wrapper">
                        <i class="ti ti-lock-check input-icon"></i>
                        <input type="password" id="password_confirm" class="form-input" placeholder="Repite tu contrasena" required autocomplete="new-password">
                    </div>
                    <span class="field-error" id="passwordConfirmError"></span>
                </div>

                <button type="button" class="btn-register" id="btnNextStep" onclick="nextStep()">
                    Siguiente <i class="ti ti-arrow-right" style="margin-left: 4px;"></i>
                </button>
            </div>

            <!-- Step 2: Organization -->
            <div id="formStep2" style="display: none;">
                <div class="form-group">
                    <label class="form-label" for="organization_name">Nombre de tu finca u organizacion</label>
                    <div class="input-wrapper">
                        <i class="ti ti-plant input-icon"></i>
                        <input type="text" id="organization_name" class="form-input" placeholder="Finca La Esperanza" required>
                    </div>
                    <span class="field-error" id="orgError"></span>
                </div>

                <div class="form-group">
                    <label class="form-label" for="phone">Telefono (opcional)</label>
                    <div class="input-wrapper">
                        <i class="ti ti-phone input-icon"></i>
                        <input type="tel" id="phone" class="form-input" placeholder="+57 300 123 4567" autocomplete="tel">
                    </div>
                </div>

                <div style="display: flex; gap: var(--space-md); margin-top: var(--space-md);">
                    <button type="button" class="btn-register btn-back" onclick="prevStep()">
                        <i class="ti ti-arrow-left"></i> Atras
                    </button>
                    <button type="submit" class="btn-register" id="btnRegister" style="flex: 1;">
                        <span class="loading-spinner"></span>
                        <span id="btnText">Crear mi cuenta gratis</span>
                    </button>
                </div>
            </div>
        </form>

        <div class="login-link">
            Ya tienes cuenta? <a href="login.html">Inicia sesion</a>
        </div>
    </div>

    <script src="../../js/register.js"></script>
</body>
</html>'''

output_path = "/Users/sebastianflorez/Documents/agrotech-digital/agrotech-client-frontend/templates/authentication/register.html"

with open(output_path, "w", encoding="utf-8") as f:
    f.write(REGISTER_HTML)

print(f"✅ register.html creado en {output_path}")
