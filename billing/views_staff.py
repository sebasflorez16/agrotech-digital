"""
Panel de Control del Operador SaaS — AgroTech Digital
Acceso exclusivo para is_staff=True / is_superuser=True.

Este módulo solo expone endpoints JSON (API REST).
El HTML del panel vive en el frontend (agrotech-client-frontend).

Rutas (public schema, sin tenant):
  GET  /staff/api/metrics/  → KPIs, ingresos, eventos   (JSON, JWT Bearer)
  GET  /staff/api/tenants/  → Lista completa de tenants  (JSON, JWT Bearer)
"""

import calendar as _calendar
from decimal import Decimal

from django.utils import timezone
from django.db.models import Count, Sum

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from base_agrotech.models import Client
from billing.models import BillingEvent, Invoice, Plan, Subscription, UsageMetrics


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _month_range(year, month):
    """Devuelve (inicio, fin) de un mes dado como objetos datetime aware."""
    from datetime import datetime
    import calendar
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime(year, month, 1), tz)
    last_day = calendar.monthrange(year, month)[1]
    end = timezone.make_aware(datetime(year, month, last_day, 23, 59, 59), tz)
    return start, end


# ──────────────────────────────────────────────
# API: Métricas / KPIs
# ──────────────────────────────────────────────

class StaffMetricsAPI(APIView):
    """
    Devuelve todos los KPIs necesarios para el dashboard del operador.

    Datos incluidos:
    - kpis: totales globales
    - revenue_history: ingresos de los últimos 6 meses
    - by_plan: distribución de tenants activos por plan
    - recent_events: últimos 25 eventos de facturación
    - top_usage: los 10 tenants con más consumo de EOSDA este mes
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        this_month_start, _ = _month_range(now.year, now.month)

        # ── Tenants (excluye public) ──────────────────────────────
        tenants_qs = Client.objects.exclude(schema_name="public")
        total_tenants = tenants_qs.count()
        new_this_month = tenants_qs.filter(created_on__gte=this_month_start).count()

        # ── Suscripciones ─────────────────────────────────────────
        subs = Subscription.objects.select_related("plan", "tenant")
        active = subs.filter(status="active").count()
        trialing = subs.filter(status="trialing").count()
        canceled = subs.filter(status="canceled").count()
        past_due = subs.filter(status="past_due").count()

        # ── MRR (suma de precios activos en COP) ──────────────────
        mrr = (
            subs.filter(status="active").aggregate(mrr=Sum("plan__price_cop"))["mrr"]
            or Decimal("0")
        )

        # ── Ingresos del mes corriente ────────────────────────────
        revenue_month = (
            Invoice.objects.filter(status="paid", paid_at__gte=this_month_start).aggregate(
                total=Sum("total")
            )["total"]
            or Decimal("0")
        )

        # ── Historial de ingresos (últimos 6 meses) ───────────────
        revenue_history = []
        for i in range(5, -1, -1):
            # mes relativo
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            m_start, m_end = _month_range(target_year, target_month)
            rev = (
                Invoice.objects.filter(
                    status="paid", paid_at__gte=m_start, paid_at__lte=m_end
                ).aggregate(t=Sum("total"))["t"]
                or Decimal("0")
            )
            revenue_history.append(
                {"month": m_start.strftime("%b %Y"), "revenue": float(rev)}
            )

        # ── Distribución por plan ─────────────────────────────────
        by_plan = [
            {"plan": row["plan__name"], "tier": row["plan__tier"], "count": row["count"]}
            for row in Subscription.objects.filter(status__in=["active", "trialing"])
            .values("plan__name", "plan__tier")
            .annotate(count=Count("id"))
            .order_by("-count")
        ]

        # ── Últimos 25 eventos ────────────────────────────────────
        events_qs = list(
            BillingEvent.objects.select_related("tenant")
            .order_by("-created_at")[:25]
            .values("created_at", "tenant__name", "event_type", "event_data")
        )
        events = []
        for e in events_qs:
            events.append({
                "created_at": e["created_at"].strftime("%Y-%m-%d %H:%M"),
                "tenant": e["tenant__name"] or "—",
                "event_type": e["event_type"],
                "description": (e.get("event_data") or {}).get("description") or e["event_type"].replace("_", " ").capitalize(),
            })

        # ── Top consumo EOSDA este mes ────────────────────────────
        top_usage = list(
            UsageMetrics.objects.filter(year=now.year, month=now.month)
            .select_related("tenant")
            .order_by("-eosda_requests")[:10]
            .values(
                "tenant__name",
                "eosda_requests",
                "hectares_used",
                "parcels_count",
                "users_count",
            )
        )

        # ── Total usuarios y parcelas (suma de métricas del mes) ───
        usage_totals = UsageMetrics.objects.filter(
            year=now.year, month=now.month
        ).aggregate(
            total_users=Sum("users_count"),
            total_parcels=Sum("parcels_count"),
        )
        total_users = usage_totals["total_users"] or 0
        total_parcels = usage_totals["total_parcels"] or 0

        # ── Facturas recientes ────────────────────────────────────
        recent_invoices = []
        for inv in Invoice.objects.select_related("tenant", "subscription__plan").order_by("-invoice_date")[:15]:
            recent_invoices.append({
                "invoice_number": inv.invoice_number,
                "tenant": inv.tenant.name if inv.tenant else "—",
                "plan": inv.subscription.plan.name if (inv.subscription and inv.subscription.plan) else "—",
                "amount": float(inv.total),
                "currency": inv.currency,
                "status": inv.status,
                "period": str(inv.invoice_date) if inv.invoice_date else "—",
                "paid_at": inv.paid_at.strftime("%Y-%m-%d") if inv.paid_at else None,
            })

        return Response(
            {
                "kpis": {
                    "total_tenants": total_tenants,
                    "active_tenants": total_tenants,
                    "new_this_month": new_this_month,
                    "active_subscriptions": active,
                    "trialing_subs": trialing,
                    "canceled_subs": canceled,
                    "past_due_subs": past_due,
                    "mrr": float(mrr),
                    "mrr_cop": float(mrr),
                    "revenue_this_month": float(revenue_month),
                    "total_users": total_users,
                    "total_parcels": total_parcels,
                },
                "revenue_history": revenue_history,
                "by_plan": by_plan,
                "recent_events": events,
                "top_usage": top_usage,
                "recent_invoices": recent_invoices,
            }
        )


# ──────────────────────────────────────────────
# API: Lista completa de tenants
# ──────────────────────────────────────────────

class StaffTenantsAPI(APIView):
    """
    Lista todos los tenants con su estado de suscripción, plan y métricas.
    Soporta búsqueda: ?search=nombre
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = (
            Client.objects.exclude(schema_name="public")
            .prefetch_related("subscription__plan")
            .order_by("-created_on")
        )
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)

        now = timezone.now()
        data = []
        for t in qs:
            sub = getattr(t, "subscription", None)
            # métricas del mes actual si existen
            usage = (
                UsageMetrics.objects.filter(
                    tenant=t, year=now.year, month=now.month
                ).first()
            )
            # Dominio (django-tenants Domain model)
            try:
                domain = t.get_primary_domain().domain if hasattr(t, "get_primary_domain") else ""
            except Exception:
                domain_qs = t.domains.first()
                domain = domain_qs.domain if domain_qs else t.schema_name
            # Último pago
            last_invoice = Invoice.objects.filter(tenant=t, status="paid").order_by("-paid_at").first()
            sub_status = sub.status if sub else "no_sub"
            data.append(
                {
                    "id": t.id,
                    "name": t.name or t.schema_name,
                    "schema": t.schema_name,
                    "domain": domain,
                    "created": t.created_on.strftime("%Y-%m-%d"),
                    "paid_until": (
                        t.paid_until.strftime("%Y-%m-%d") if t.paid_until else None
                    ),
                    "plan": sub.plan.name if sub and sub.plan else "Starter",
                    "tier": sub.plan.tier if sub and sub.plan else "starter",
                    "status": sub_status,
                    "is_active": sub_status == "active",
                    "on_trial": sub_status == "trialing",
                    "gateway": sub.payment_gateway if sub else "—",
                    "eosda_requests": usage.eosda_requests if usage else 0,
                    "hectares_used": float(usage.hectares_used) if usage else 0,
                    "parcel_count": usage.parcels_count if usage else 0,
                    "user_count": usage.users_count if usage else 0,
                    "last_payment": last_invoice.paid_at.strftime("%Y-%m-%d") if last_invoice and last_invoice.paid_at else None,
                }
            )

        return Response({"tenants": data, "total": len(data)})
