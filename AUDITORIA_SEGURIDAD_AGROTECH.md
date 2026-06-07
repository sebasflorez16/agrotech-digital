# 🔐 AUDITORÍA DE SEGURIDAD — AGROTECH DIGITAL

**Fecha**: 6 de junio de 2026
**Alcance**: Revisión completa del código fuente del proyecto Agrotech Digital
**Foco principal**: Fuga de datos entre fincas (multi-tenant), autenticación, autorización, secretos, configuración de seguridad
**Repositorio**: `github.com/sebasflorez16/agrotech-digital`

---

## RESUMEN EJECUTIVO

| Severidad | Cantidad | Descripción |
|-----------|----------|-------------|
| 🔴 **Crítica** | 5 | Fugas de datos entre tenants, credenciales hardcodeadas, falta de defensa en profundidad |
| 🟠 **Alta** | 6 | Endpoints sin filtro de tenant, validación de pertenencia ausente, CORS abierto |
| 🟡 **Media** | 5 | Logging de datos sensibles, rate limiting débil, configuración redundante insegura |
| 🟢 **Baja** | 3 | Buenas prácticas pendientes, documentación de seguridad |

---

## 🔴 VULNERABILIDADES CRÍTICAS

### CRIT-1: Ausencia de defensa en profundidad multi-tenant a nivel de aplicación

**Descripción**: El proyecto usa `django-tenants` con aislamiento por esquema PostgreSQL. De los ~20 modelos del proyecto, **solo 2** (`CacheDatosEOSDA`, `EstadisticaUsoEOSDA`) tienen campo `tenant_id` explícito. Los demás modelos (`Parcel`, `Crop`, `Labor`, `Employee`, `InventoryItem`, `CropCycle`, etc.) dependen **exclusivamente** del routing de esquema de PostgreSQL. Si ocurre un bug en `django-tenants`, una mala configuración del middleware, o un error de conexión de BD, un tenant podría acceder a datos de otro tenant.

**Archivos afectados**:
- `parcels/models.py` — `Parcel`, `ParcelActionLog`, `ParcelSceneCache`, `AnalyticsResult`, `CachedImage`, `NDVIAnalysis`, `WaterStressAnalysis`, `CropHealthStatus`, `CacheDatosEOSDA` (✅ ya tiene tenant_id), `EstadisticaUsoEOSDA` (✅ ya tiene tenant_id)
- `crop/models.py` — `Crop`, `CropCycle`, `CropType`
- `labores/models.py` — `Labor`, `LaborType`
- `inventario/models.py` — `InventoryItem`, `Warehouse`
- `RRHH/models.py` — `Employee`, `Role`, `Department`
- `billing/models.py` — Modelos de suscripción (no requieren tenant_id pues están en schema `public`)

**Riesgo**: Si el schema routing falla, un usuario de la Finca A podría ver/editar parcelas, cultivos, empleados e inventario de la Finca B.

**Fix Plan**:
1. Agregar campo `tenant_id = models.ForeignKey('base_agrotech.Client', ...)` a TODOS los modelos que residen en esquemas de tenant (no en `public`)
2. Implementar un manager personalizado con filtro automático por tenant
3. Agregar migración de datos para backfill desde el schema actual
4. Agregar tests de integración que validen que un tenant nunca ve datos de otro

---

### CRIT-2: Endpoints API sin filtro explícito por tenant

**Descripción**: Los ViewSets DRF en `parcels/views.py`, `crop/views.py`, `labores/views.py`, `inventario/views.py`, `RRHH/views.py` y `parcels/analytics_views.py` **nunca filtran explícitamente por tenant**. Dependen 100% de que `django-tenants` haga el routing de conexión de BD. No hay `queryset = Model.objects.filter(tenant=request.tenant)` ni similar.

**Endpoints vulnerables** (lista parcial):
- `ParcelViewSet` — `list`, `retrieve`, `update`, `destroy`, `summary`, `ndvi_historical`, `water_stress_historical`
- `CropTypeViewSet` — todos los métodos CRUD
- `CropViewSet` — todos los métodos CRUD
- `CropCycleViewSet` — todos los métodos CRUD
- `LaborViewSet` — todos los métodos CRUD
- `EmployeeViewSet` — todos los métodos CRUD
- `InventoryItemViewSet` — todos los métodos CRUD
- `WarehouseViewSet` — todos los métodos CRUD
- `EOSDASearchView`, `EOSDAImageView`, `ScenesByDateView`, `AnalyticsView` — operaciones con parcelas sin validación de pertenencia

**Riesgo**: Si un atacante manipula el hostname, header `X-Tenant-Domain` o explota un race condition en el middleware, puede acceder a datos de otros tenants.

**Fix Plan**:
1. Implementar mixin `TenantScopedQuerySetMixin` que sobreescriba `get_queryset()` en cada ViewSet
2. Agregar `filter(tenant=request.tenant)` al queryset base de cada vista
3. En vistas de detalle (retrieve/update/destroy), validar que el objeto pertenece al tenant del request
4. Agregar tests para cada endpoint con tenants cruzados

---

### CRIT-3: Contraseña de base de datos hardcodeada en código fuente

**Descripción**: El archivo `config/settings/test.py` contiene una contraseña de PostgreSQL en texto plano:

```python
DATABASES = {
    'default': {
        'PASSWORD': 'guibsonsid.16',  # ← CONTRASEÑA REAL
        ...
    }
}
```

Este archivo está versionado en git (`config/settings/test.py`). Cualquiera con acceso al repositorio puede ver la contraseña.

**Riesgo**: Acceso no autorizado a la base de datos de desarrollo/testing, que podría contener datos reales si se usa el mismo servidor. Además, si la misma contraseña se usa en producción, es un riesgo catastrófico.

**Fix Plan**:
1. **INMEDIATO**: Cambiar la contraseña de la BD de desarrollo/testing
2. Eliminar la contraseña hardcodeada de `test.py`
3. Usar `env("DATABASE_PASSWORD", default="")` sin fallback inseguro
4. Ejecutar `git filter-branch` o `BFG Repo-Cleaner` para eliminar la contraseña del historial de git
5. Rotar credenciales de BD en todos los entornos

---

### CRIT-4: SECRET_KEY de Django con fallback inseguro en desarrollo

**Descripción**: `config/settings/local.py` y `config/settings/test.py` definen:

```python
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-*eavrb@@3e%_qbd8#*4kvr%rq@nhkw3=k_pkxvw$+g&huq%!pj",
)
```

Si por error se despliega `local.py` en producción (o Railway toma la configuración incorrecta), la SECRET_KEY sería conocida públicamente (está en el historial de git). Esto compromete sesiones, tokens JWT, CSRF y cualquier dato firmado criptográficamente.

**Riesgo**: Robo de sesiones, suplantación de usuarios, falsificación de tokens JWT, bypass de firma CSRF.

**Fix Plan**:
1. Eliminar el `default=` inseguro de `local.py` y `test.py`
2. Para desarrollo local, generar una clave automáticamente en `start_dev_server.sh`
3. Asegurar que `production.py` fuerce `env("DJANGO_SECRET_KEY")` sin default
4. Agregar validación al inicio de la app: rechazar SECRET_KEYs que empiecen con "django-insecure-"

---

### CRIT-5: CORS potencialmente abierto a cualquier origen

**Descripción**: La configuración CORS en `base.py` define `CORS_ALLOW_ALL_ORIGINS = True` (línea ~400). Aunque `production.py` lo sobrescribe, el middleware `dynamic_cors.py` en `authentication/middlewares/` está **completamente comentado** (no se ejecuta). Esto significa que en producción podrían quedar orígenes abiertos si no se configura correctamente la variable `CORS_ALLOWED_ORIGINS`.

**Archivos**:
- `config/settings/base.py` — `CORS_ALLOW_ALL_ORIGINS = True`
- `config/settings/production.py` — Depende de `env("CORS_ALLOWED_ORIGINS", default="")`
- `authentication/middlewares/dynamic_cors.py` — **Completamente comentado, no funciona**

**Riesgo**: Cualquier dominio malicioso podría hacer requests cross-origin a la API autenticada, robando tokens JWT del localStorage.

**Fix Plan**:
1. Verificar que `production.py` tenga `CORS_ALLOW_ALL_ORIGINS = False`
2. Configurar `CORS_ALLOWED_ORIGINS` explícitamente con los dominios de producción
3. Activar el middleware `dynamic_cors.py` descomentándolo o eliminarlo si no se usa
4. Agregar `CORS_ALLOW_CREDENTIALS = True` solo si es necesario

---

## 🟠 VULNERABILIDADES ALTAS

### HIGH-1: Validación de pertenencia de parcela al tenant ausente en operaciones con ID por URL

**Descripción**: Endpoints como `ParcelViewSet.retrieve()`, `.update()`, `.destroy()`, y vistas analíticas como `NDVIHistoricalView`, `WaterStressHistoricalView`, `AnalyticsView` reciben un `parcel_id` por URL pero **nunca validan** que ese `parcel_id` pertenezca al tenant del usuario autenticado.

**Ejemplo**:
```python
# parcels/views.py - NDVIHistoricalView
parcel = Parcel.objects.get(id=parcel_id)  # ← No verifica tenant
```

**Riesgo**: Un usuario de la Finca A podría adivinar/descubrir el ID de una parcela de la Finca B y acceder a datos de NDVI, imágenes satelitales, etc.

**Fix Plan**:
1. Agregar validación en cada endpoint: `parcel = Parcel.objects.get(id=parcel_id, tenant=request.tenant)`
2. O usar `get_object_or_404(Parcel, id=parcel_id, tenant=request.tenant)`
3. Implementar helper `get_tenant_parcel(request, parcel_id)` centralizado

---

### HIGH-2: Endpoint nativo de DRF SimpleJWT expuesto en paralelo

**Descripción**: `config/urls.py` expone el `TokenObtainPairView` nativo de DRF SimpleJWT (`POST /api/token/`), en paralelo al `LoginView` personalizado (`POST /api/auth/login/`). Esto crea dos rutas que emiten tokens JWT con comportamientos diferentes y potencialmente inconsistentes.

**Riesgo**: 
- El endpoint `/api/token/` podría no ejecutar la lógica multi-tenant de `LoginView` (asignación correcta de tenant al token)
- Podría emitir tokens sin el claim de `tenant_id` o `tenant_domain`
- Duplica la superficie de ataque para fuerza bruta

**Fix Plan**:
1. Eliminar `path('api/token/', TokenObtainPairView.as_view())` de `config/urls.py`
2. Mantener solo `POST /api/auth/login/` como único endpoint de obtención de tokens
3. Si se necesita mantener SimpleJWT nativo, asegurar que los serializadores inyecten el tenant en el payload

---

### HIGH-3: Endpoints de gestión de usuarios sin protección de tenant

**Descripción**: En `config/urls.py` hay rutas HTML para gestión de usuarios:
- `GET /users/all/` — `UsersListView`
- `POST /users/create/` — `UserCreateView`  
- `GET /users/detail/<pk>/` — `UserDetailView`
- `PUT /users/edit/<int:pk>/` — `UserUpdateView`

Estas vistas se ejecutan en el esquema `public` pero **no validan que el usuario administrador pertenezca al tenant que está gestionando**, ni limitan los usuarios listados/creados al tenant del admin.

**Riesgo**: Un administrador de la Finca A podría ver/editar usuarios de la Finca B.

**Fix Plan**:
1. Agregar filtro `user.tenant == request.user.tenant` en todas las vistas de gestión de usuarios
2. Restringir `UserDetailView` y `UserUpdateView` a usuarios del mismo tenant
3. Eliminar rutas HTML no esenciales o migrarlas a API con autenticación robusta

---

### HIGH-4: Ausencia de refresh token rotation

**Descripción**: El sistema JWT usa `djangorestframework-simplejwt` con refresh tokens, pero **no implementa refresh token rotation**. Un refresh token robado puede usarse indefinidamente hasta que expire.

**Riesgo**: Si un refresh token es robado (XSS, localStorage access), el atacante puede generar access tokens indefinidamente sin ser detectado, incluso si el usuario cambia su contraseña.

**Fix Plan**:
1. Activar `ROTATE_REFRESH_TOKENS = True` en la configuración de SimpleJWT
2. Activar `BLACKLIST_AFTER_ROTATION = True`
3. Agregar el modelo `OutstandingToken` y `BlacklistedToken` de SimpleJWT
4. Ejecutar migraciones pendientes de `rest_framework_simplejwt.token_blacklist`

---

### HIGH-5: Ausencia de rate limiting en endpoints de autenticación de SimpleJWT

**Descripción**: El endpoint `POST /api/token/` de SimpleJWT nativo **no tiene throttle** aplicado, mientras que `LoginView` tiene `throttle_classes = [AnonRateThrottle]` con `10/minute`. Esto deja una ruta de fuerza bruta sin protección.

**Riesgo**: Ataques de fuerza bruta contra credenciales de usuarios.

**Fix Plan**:
1. Ver HIGH-2: eliminar el endpoint duplicado `/api/token/`
2. Si se mantiene, agregar `throttle_classes` a `TokenObtainPairView`
3. Aumentar el throttle en `LoginView` a `5/minute` para producción

---

### HIGH-6: Posible logging de datos sensibles en EOSDA

**Descripción**: El código en `parcels/views.py` loguea headers y payloads de requests a la API de EOSDA (líneas 148-155):

```python
logger.info(f"[SCENES_BY_DATE] Payload enviado: {payload}")
# NOTA: No loguear headers para no exponer la API key
```

Aunque menciona no loguear headers (lo cual es correcto), los payloads y respuestas completas se loguean y podrían contener datos de parcelas (coordenadas, geometrías) que son datos sensibles del tenant.

**Riesgo**: Fuga de datos de parcelas/clientes a través de logs.

**Fix Plan**:
1. Reducir el nivel de logging de payloads/respuestas EOSDA a DEBUG
2. Sanitizar logs removiendo coordenadas y geometrías
3. En producción, configurar `LOGGING` para que los logs de EOSDA vayan a un archivo separado con retención limitada

---

## 🟡 VULNERABILIDADES MEDIAS

### MED-1: SmartTenantMiddleware con resolución por header X-Tenant-Domain manipulable

**Descripción**: `config/middleware.py:96` — `SmartTenantMiddleware` resuelve el tenant desde el header `X-Tenant-Domain` si no hay JWT. Aunque hace verificación cruzada con JWT cuando ambos están presentes, si un request no tiene JWT (ej: rutas que AllowAny), el header es la única fuente de verdad.

**Riesgo**: Un atacante podría manipular el header `X-Tenant-Domain` en requests sin autenticación para acceder al esquema de otro tenant. Las rutas AllowAny son limitadas (login, register), pero el riesgo existe.

**Fix Plan**:
1. Eliminar la resolución por header `X-Tenant-Domain` en producción
2. Usar solo JWT (requests autenticados) y hostname para la resolución de tenant
3. Agregar validación: solo permitir tenants vía header si el request viene de un IP interno/admin

---

### MED-2: Rate limiting débil en registro

**Descripción**: `RegisterView` usa `throttle_classes = [AnonRateThrottle]` con `5/hour`. Esto es bajo para un SaaS legítimo pero **no tiene protección contra creación masiva de cuentas con diferentes IPs** (botnets).

**Fix Plan**:
1. Agregar CAPTCHA (reCAPTCHA v3) al endpoint de registro
2. Agregar validación de email (email verification) antes de activar la cuenta
3. Limitar registros por dominio de email o por rango de IP

---

### MED-3: Configuración SESSION_COOKIE_SECURE no definida en base.py

**Descripción**: `config/settings/base.py` **no define** `SESSION_COOKIE_SECURE`, dejándolo en `False` por defecto de Django. Aunque `production.py` lo sobrescribe a `True`, si se usa `local.py` o `test.py` con HTTPS, las cookies de sesión se enviarían sin flag `Secure`.

**Fix Plan**:
1. Agregar `SESSION_COOKIE_SECURE = not DEBUG` en `base.py`
2. Agregar `CSRF_COOKIE_SECURE = not DEBUG` en `base.py`

---

### MED-4: Archivos .md sensibles en el repositorio

**Descripción**: El repositorio contiene ~50 archivos `.md` con documentación técnica que incluye nombres de servicios, arquitectura, y posiblemente datos de configuración. Archivos como `CONFIGURACION_ENTORNOS.md`, `DEPLOYMENT.md`, `railway-config.md` pueden revelar detalles de infraestructura a atacantes.

**Riesgo**: Information disclosure. Un atacante que obtenga acceso al repo (público?) puede mapear toda la infraestructura.

**Fix Plan**:
1. Revisar si el repositorio debe ser privado (en GitHub)
2. Mover documentación sensible a un wiki interno
3. Si el repo es público, sanitizar archivos `.md` removiendo URLs internas, nombres de servicios, etc.

---

### MED-5: Falta de Content Security Policy (CSP)

**Descripción**: No se configura `Content-Security-Policy` en los headers de respuesta. Esto deja la app vulnerable a ataques XSS si se logra inyectar scripts maliciosos.

**Fix Plan**:
1. Agregar middleware `django-csp` o configurar headers manualmente
2. Definir política CSP restrictiva: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'`
3. Usar nonces para estilos inline necesarios

---

## 🟢 VULNERABILIDADES BAJAS

### LOW-1: DEBUG Toolbar expuesto en configuración

**Descripción**: `config/settings/base.py` tiene `DEBUG_TOOLBAR_CONFIG` y referencias a `debug_toolbar`. Aunque está condicionado a `DEBUG=True`, es código innecesario en archivos de producción.

**Riesgo**: Si por error se activa DEBUG en producción, la toolbar expone queries SQL, variables de settings, y datos de request.

**Fix Plan**:
1. Mover toda la configuración de debug_toolbar a `local.py` exclusivamente
2. Agregar guarda en `base.py`: solo cargar debug_toolbar si `DEBUG` e `INSTALLED_APPS` condicional

---

### LOW-2: Archivos de test con datos reales potenciales

**Descripción**: `test_saas_complete.py`, `test_complete_saas_flow.py`, `crear_usuario_test.py` contienen scripts que interactúan con el sistema real (no son tests unitarios aislados). Si se ejecutan contra producción, podrían crear datos basura.

**Fix Plan**:
1. Mover scripts a `/scripts/` con prefijo `dev_`
2. Agregar validación que rechace ejecución si `DEBUG=False`
3. Documentar claramente que son para desarrollo local

---

### LOW-3: Modelo User sin soft delete

**Descripción**: `authentication/models.py` — el modelo `User` no tiene campo `is_active` para soft delete, ni manejo de eliminación de datos personales (GDPR).

**Fix Plan**:
1. Agregar campo `is_active` con default `True`
2. Implementar soft delete en usuarios
3. Agregar endpoint de eliminación de cuenta con anonimización de datos

---

## 📊 PLAN DE CORRECCIÓN (FIX PLAN) — PRIORIZADO

### FASE 1 — INMEDIATO (0-24 horas) 🔴

| ID | Acción | Archivos | Esfuerzo |
|----|--------|----------|----------|
| CRIT-3 | **Rotar contraseña BD**: Cambiar `guibsonsid.16` inmediatamente. Eliminar hardcodeo. Usar variable de entorno. | `config/settings/test.py` | 30 min |
| CRIT-4 | **Eliminar default inseguro de SECRET_KEY**: Sin fallback en local/test. | `config/settings/local.py`, `config/settings/test.py` | 15 min |
| CRIT-5 | **Revisar CORS en producción**: Verificar `CORS_ALLOWED_ORIGINS` en Railway. Poner `CORS_ALLOW_ALL_ORIGINS = False`. | `config/settings/production.py`, Railway env vars | 30 min |
| HIGH-4 | **Activar refresh token rotation y blacklist**: `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`. Migrar blacklist. | `config/settings/base.py`, migraciones | 45 min |
| HIGH-2 | **Eliminar endpoint duplicado `/api/token/`**: Dejar solo `LoginView`. | `config/urls.py` | 15 min |

### FASE 2 — CORTO PLAZO (1-7 días) 🟠

| ID | Acción | Archivos | Esfuerzo |
|----|--------|----------|----------|
| CRIT-1 | **Agregar `tenant_id` a todos los modelos de tenant**: ForeignKey a `base_agrotech.Client`. Backfill migración. | `parcels/models.py`, `crop/models.py`, `labores/models.py`, `inventario/models.py`, `RRHH/models.py` | 8h |
| CRIT-2 | **Implementar `TenantScopedQuerySetMixin`**: Filtrado automático en todos los ViewSets. | `parcels/views.py`, `crop/views.py`, `labores/views.py`, `inventario/views.py`, `RRHH/views.py` | 6h |
| HIGH-1 | **Validar pertenencia de parcela al tenant**: En cada endpoint con `parcel_id`. | `parcels/views.py`, `parcels/analytics_views.py`, `parcels/metrics_views.py`, `parcels/eosda_optimized_views.py` | 4h |
| HIGH-5 | **Agregar rate limiting a todos los endpoints de auth**: Throttle en SimpleJWT si se mantiene. | `config/urls.py`, `authentication/views.py` | 1h |
| MED-1 | **Eliminar resolución de tenant por header `X-Tenant-Domain`**: Solo JWT + hostname. | `config/middleware.py` | 2h |

### FASE 3 — MEDIO PLAZO (1-4 semanas) 🟡

| ID | Acción | Archivos | Esfuerzo |
|----|--------|----------|----------|
| HIGH-3 | **Proteger vistas de gestión de usuarios**: Filtrar por tenant. | `authentication/views.py` (vistas HTML) | 3h |
| HIGH-6 | **Sanitizar logs de EOSDA**: Reducir nivel, remover coordenadas. | `parcels/views.py`, `config/logging_config.py` | 2h |
| MED-2 | **Agregar CAPTCHA a registro**: reCAPTCHA v3. | `authentication/views.py`, `authentication/forms.py` | 4h |
| MED-3 | **Agregar `SESSION_COOKIE_SECURE = not DEBUG`**: En base.py. | `config/settings/base.py` | 15 min |
| MED-5 | **Configurar Content-Security-Policy**: Headers CSP. | `config/middleware.py` | 3h |
| CRIT-3 | **Limpiar historial de git**: `git filter-branch` para remover contraseña. | Repositorio git | 2h |

### FASE 4 — LARGO PLAZO (1-3 meses) 🟢

| ID | Acción | Archivos | Esfuerzo |
|----|--------|----------|----------|
| CRIT-1 | **Tests de integración multi-tenant**: Suite de tests que validen aislamiento. | Todos los módulos | 16h |
| LOW-1 | **Mover debug_toolbar a local.py**: Eliminar de base.py. | `config/settings/base.py`, `local.py` | 1h |
| LOW-2 | **Reorganizar scripts de test**: Mover a `/scripts/dev_*`. | Varios | 1h |
| LOW-3 | **Implementar soft delete y GDPR**: `is_active`, anonimización. | `authentication/models.py`, `views.py` | 6h |
| MED-4 | **Revisar privacidad del repositorio**: Sanitizar .md públicos. | Documentación | 4h |

---

## 📋 CHECKLIST DE VERIFICACIÓN POST-CORRECCIÓN

- [ ] `tenant_id` existe en todos los modelos de esquema de tenant
- [ ] Todos los ViewSets usan `TenantScopedQuerySetMixin`
- [ ] Todos los endpoints con `parcel_id` validan pertenencia al tenant
- [ ] No hay contraseñas/keys hardcodeadas en el código fuente (`grep -r "PASSWORD\|SECRET_KEY\|API_KEY" --include="*.py" | grep -v "env("`)
- [ ] CORS restringido a dominios de producción
- [ ] Refresh token rotation activo
- [ ] Un solo endpoint de login (`POST /api/auth/login/`)
- [ ] Rate limiting en todos los endpoints de autenticación
- [ ] Historial de git limpiado de contraseñas
- [ ] Tests multi-tenant pasando (`python manage.py test --settings=config.settings.test`)
- [ ] CSP headers configurados en producción

---

## 🛡️ RESUMEN DE POSTURA DE SEGURIDAD

| Área | Calificación | Notas |
|------|-------------|-------|
| Aislamiento multi-tenant | ⚠️ Regular | django-tenants funciona pero sin defensa en profundidad |
| Autenticación | ✅ Buena | JWT con SimpleJWT, login personalizado, throttle |
| Autorización | ⚠️ Regular | No hay validación explícita de pertenencia en vistas |
| Secretos | ❌ Débil | Contraseña hardcodeada, SECRET_KEY con default |
| CORS | ⚠️ Regular | Configuración potencialmente abierta |
| Logging | ⚠️ Regular | Posible fuga de datos sensibles en logs |
| Infraestructura | ✅ Buena | Railway con variables de entorno para producción |
| Cumplimiento GDPR | ❌ Débil | Sin soft delete ni anonimización |

---

*Auditoría generada por análisis automatizado + revisión manual de código — 6 de junio de 2026*