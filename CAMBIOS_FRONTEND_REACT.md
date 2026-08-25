# Cambios del frontend React (repo `agrotech-client-frontend`)

> El frontend React se maneja en un repo **separado**:
> `https://github.com/sebasflorez16/agrotech-client-frontend.git` (deploy en Netlify).
>
> Estos son los **3 archivos** que cambié. Aplica estos cambios en ese repo
> (no en `agrotech-digital`).

---

## 1. `src/api/client.js` — corregir `register()` para alinear con el backend

**Antes:**
```js
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
```

**Después:**
```js
export async function register({ username, email, password, name, last_name, organization_name }) {
  const { data } = await api.post("/api/auth/register/", {
    username,
    email,
    password,
    password_confirm: password,
    name,
    last_name,
    organization_name,
  });
  return data;
}
```

---

## 2. `src/pages/Register.jsx` — campo `name` + `organization_name`

Cambios puntuales:

1. Estado del formulario (quitar `first_name`, agregar `name` y `organization_name`):
```js
const [form, setForm] = useState({
  name: "",
  last_name: "",
  email: "",
  username: "",
  organization_name: "",
  password: "",
  confirmPassword: "",
});
```

2. Llamada a `register(...)`:
```js
await register({
  name: form.name,
  last_name: form.last_name,
  email: form.email,
  username: form.username,
  organization_name: form.organization_name,
  password: form.password,
});
```

3. El input de "Nombre" usa `form.name` / `update("name")` (antes `first_name`).

4. Agregar un input nuevo después del de "Nombre de usuario":
```jsx
<div>
  <label className="block text-sm font-medium text-[#6E6E73] mb-1">Nombre de la finca / empresa</label>
  <input
    type="text"
    required
    value={form.organization_name}
    onChange={update("organization_name")}
    className="glass-input text-sm py-2.5"
    placeholder="Finca El Roble"
  />
</div>
```

---

## 3. `src/pages/Landing.jsx` — quitar "EOSDA" de los planes (3 líneas)

Cambiar:
- `"10 consultas EOSDA/mes"` → `"10 análisis satelitales/mes"`
- `"100 consultas EOSDA/mes"` → `"100 análisis satelitales/mes"`
- `"300 consultas EOSDA/mes"` → `"300 análisis satelitales/mes"`

---

### Verificación rápida
- `npm run build` debe compilar sin errores.
- En producción (Netlify) el registro debe funcionar: al registrar, el backend recibe
  `name`, `last_name`, `organization_name`, `password_confirm` (no `first_name`/`password2`).
