# Meta Ads — checklist de lanzamiento (AgroTech Digital)

> No publicar campañas de compra hasta completar los gates de pagos (Fase 5).
> Se puede iniciar captación de leads cuando el tracking esté validado.

## 1. Variables de entorno (backend)

| Variable | Ejemplo | Obligatoria |
|---|---|---|
| `META_PIXEL_ID` | `1521929183273863` | Sí |
| `META_CAPI_ACCESS_TOKEN` | token de Conversions API | Sí para CAPI |
| `META_CAPI_ENABLED` | `True` | Sí |
| `META_CAPI_TEST_EVENT_CODE` | `TEST123` (solo pruebas) | No |
| `META_GRAPH_API_VERSION` | `v20.0` | No |
| `FRONTEND_URL` | `https://agrotechcolombia.com` | Sí |
| `SITE_URL` | `https://agrotech-digital-production.up.railway.app` | Sí |

## 2. Eventos implementados

| Evento Meta | Dónde | Deduplicación |
|---|---|---|
| `PageView` | `js/meta-tracking.js` (tras consentimiento) | Automática |
| `ViewContent` | pricing, plan-detail | — |
| `Lead` | submit del formulario de registro | — |
| `CompleteRegistration` | registro exitoso (pixel + CAPI) | `event_id` del registro |
| `InitiateCheckout` | carga de checkout | — |
| `Purchase` | pago confirmado (pixel + CAPI) | `purchase_{reference}` |
| `Subscribe` | renovación Wompi (CAPI) | `subscribe_{reference}_{tx}` |
| `Contact` | pendiente: clic WhatsApp | — |

El pixel **solo se carga si la persona acepta** cookies de marketing. El CAPI
respeta `marketing_consent` enviado por el frontend.

## 3. Pruebas antes de pautar

1. Abrir `https://agrotechcolombia.com` en incógnito.
2. Aceptar cookies.
3. Verificar en **Meta Events Manager → Test Events**:
   - `PageView` al navegar.
   - `ViewContent` en `/templates/billing/pricing.html`.
   - `Lead` al enviar el registro.
   - `CompleteRegistration` tras crear la cuenta.
   - `Purchase` tras un pago aprobado en Wompi sandbox.
4. Confirmar que `Purchase` llega **una sola vez** y con `value` y `COP`.
5. Rechazar cookies en otro navegador: no deben salir eventos de marketing.
6. Verificar que el pixel viejo (`936082032542696`) ya no se usa.
7. Confirmar que el dominio está verificado en Business Manager.

## 4. Estructura de campaña inicial (test)

- **Objetivo:** Leads (WhatsApp/formulario) o Ventas, según la oferta activa.
- **Presupuesto:** COP 80.000–120.000/día durante 14 días.
- **Conjuntos (3–4):**
  1. Amplio Colombia (Advantage+).
  2. Intereses: agricultura, agronegocios, café, arroz, cacao, aguacate, ganadería.
  3. Lookalike 1–3% de registrados.
  4. Retargeting 30 días (visitantes y registro sin activar).
- **Excluir:** clientes actuales, empleados, compradores.
- **Creativos:** 3 ángulos × 3 formatos (reel 9:16, feed 4:5, carrusel).
- **UTMs:** `utm_source=meta&utm_medium=paid&utm_campaign=...&utm_content=...&utm_term=...`.

## 5. KPIs y criterios de corte

| Métrica | Objetivo | Cortar si |
|---|---|---|
| CTR | > 1,5% | < 1% |
| CPC | < COP 2.500 | > COP 3.500 |
| CPL | < COP 25.000 | > COP 40.000 |
| Landing → registro | > 2,5% | < 1,5% |
| Registro → activación | > 40% | < 20% |
| Activado → pago | > 15% | < 5% |
| CAC Básico | < COP 150.000 | > COP 300.000 |
| Payback | < 3 meses | > 6 meses |

## 6. Reglas de atribución

- Un solo pixel de marca.
- Un solo dominio canónico: `agrotechcolombia.com`.
- No usar el sitio viejo de Netlify en anuncios.
- Mantener `fbclid` y UTMs en el registro y el checkout.
- Revisar semanalmente la calidad de coincidencia del CAPI (Event Match Quality).

## 7. Pendientes antes de escalar

- [ ] Enviar `Contact` al hacer clic en WhatsApp.
- [ ] Enviar `AddPaymentInfo` antes de abrir el widget de Wompi.
- [ ] Implementar `ViewContent` en las páginas de servicio.
- [ ] Revisar claims y políticas de Meta (evitar “precisión milimétrica” y ahorros no comprobados).
- [ ] Probar el pixel en iOS con bloqueo de tracking y verificar CAPI.
