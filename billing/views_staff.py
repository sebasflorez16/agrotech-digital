"""
Panel de Control del Operador SaaS — AgroTech Digital
====================================================
Doble verificacion de acceso: is_staff + is_superuser + StaffAccessKey.

Endpoints JSON (requieren JWT Bearer + X-Staff-Access-Key):
  GET  /staff/                     → Panel HTML
  GET  /staff/api/metrics/        → KPIs, ingresos, eventos
  GET  /staff/api/tenants/        → Listado completo de clientes
  GET  /staff/api/tenants/{id}/   → Detalle completo de un cliente
  POST /staff/api/tenants/{id}/suspend/    → Suspender tenant
  POST /staff/api/tenants/{id}/activate/   → Reactivar tenant
  POST /staff/api/tenants/{id}/change-plan/ → Cambiar plan
  GET  /staff/api/financials/     → Facturas, revenue, MRR detallado
"""

import calendar as _calendar
import os
from datetime import datetime, timedelta, date
from decimal import Decimal

from django.db.models import Count, Sum, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from base_agrotech.models import Client
from billing.models import (
    BillingEvent, Invoice, Plan, Subscription, UsageMetrics
)
from billing.permissions import StaffAccessPermission


# ─── Helpers ───────────────────────────────────────────────────

def _month_range(year, month):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime(year, month, 1), tz)
    last_day = _calendar.monthrange(year, month)[1]
    end = timezone.make_aware(datetime(year, month, last_day, 23, 59, 59), tz)
    return start, end


def _tenant_summary(t, now=None):
    """Construye el diccionario resumen para un tenant."""
    if now is None:
        now = timezone.now()
    sub = getattr(t, "subscription", None)
    usage = UsageMetrics.objects.filter(
        tenant=t, year=now.year, month=now.month
    ).first()

    try:
        domain = t.get_primary_domain().domain if hasattr(t, "get_primary_domain") else t.schema_name
    except Exception:
        domain_qs = t.domains.first()
        domain = domain_qs.domain if domain_qs else t.schema_name

    last_invoice = Invoice.objects.filter(tenant=t, status="paid").order_by("-paid_at").first()
    sub_status = sub.status if sub else "no_sub"

    return {
        "id": t.id,
        "name": t.name or t.schema_name,
        "schema": t.schema_name,
        "domain": domain,
        "created": t.created_on.strftime("%Y-%m-%d") if t.created_on else None,
        "paid_until": t.paid_until.strftime("%Y-%m-%d") if t.paid_until else None,
        "plan": sub.plan.name if sub and sub.plan else "—",
        "tier": sub.plan.tier if sub and sub.plan else "—",
        "status": sub_status,
        "is_active": sub_status == "active",
        "on_trial": sub_status == "trialing",
        "gateway": sub.payment_gateway if sub else "—",
        "eosda_requests": usage.eosda_requests if usage else 0,
        "hectares_used": float(usage.hectares_used) if usage else 0,
        "parcel_count": usage.parcels_count if usage else 0,
        "user_count": usage.users_count if usage else 0,
        "last_payment": (
            last_invoice.paid_at.strftime("%Y-%m-%d")
            if last_invoice and last_invoice.paid_at else None
        ),
        "last_payment_amount": float(last_invoice.total) if last_invoice else 0,
    }


# ═══════════════════════════════════════════════════════════════
#  PANEL HTML (sin auth en el servidor, el JS maneja login)
# ═══════════════════════════════════════════════════════════════

class StaffDashboardView(View):
    """Sirve el panel HTML del operador. La autenticación la maneja el JS."""

    def get(self, request):
        from django.conf import settings

        html_path = os.path.join(
            str(settings.APPS_DIR),
            "..", "metrica", "static", "templates", "staff", "dashboard.html"
        )
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                return HttpResponse(f.read(), content_type="text/html; charset=utf-8")
        except FileNotFoundError:
            return HttpResponse(
                "<h1>Panel no disponible</h1><p>El archivo HTML no se encontró en el servidor.</p>",
                status=404,
            )


# ═══════════════════════════════════════════════════════════════
#  MÉTRICAS / KPIs
# ═══════════════════════════════════════════════════════════════

class StaffMetricsAPI(APIView):
    """
    Dashboard principal del operador: KPIs, revenue, eventos, consumo.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser, StaffAccessPermission]

    def get(self, request):
        now = timezone.now()
        this_month_start, _ = _month_range(now.year, now.month)

        # ── Tenants ──────────────────────────────────────────
        tenants_qs = Client.objects.exclude(schema_name="public")
        total_tenants = tenants_qs.count()
        new_this_month = tenants_qs.filter(created_on__gte=this_month_start).count()

        # ── Suscripciones ─────────────────────────────────────
        subs = Subscription.objects.select_related("plan", "tenant")
        active = subs.filter(status="active").count()
        trialing = subs.filter(status="trialing").count()
        canceled = subs.filter(status="canceled").count()
        past_due = subs.filter(status="past_due").count()

        # ── MRR ───────────────────────────────────────────────
        mrr = (
            subs.filter(status="active").aggregate(mrr=Sum("plan__price_cop"))["mrr"]
            or Decimal("0")
        )

        # ── Ingresos del mes ─────────────────────────────────
        revenue_month = (
            Invoice.objects.filter(status="paid", paid_at__gte=this_month_start)
            .aggregate(total=Sum("total"))["total"]
            or Decimal("0")
        )

        # ── Revenue history (12 meses) ───────────────────────
        revenue_history = []
        for i in range(11, -1, -1):
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
            revenue_history.append({
                "month": m_start.strftime("%b %Y"), "revenue": float(rev)
            })

        # ── Por plan ─────────────────────────────────────────
        by_plan = [
            {"plan": row["plan__name"], "tier": row["plan__tier"], "count": row["count"]}
            for row in Subscription.objects.filter(
                status__in=["active", "trialing"]
            ).values("plan__name", "plan__tier").annotate(count=Count("id")).order_by("-count")
        ]

        # ── Eventos ──────────────────────────────────────────
        events_qs = list(
            BillingEvent.objects.select_related("tenant")
            .order_by("-created_at")[:25]
            .values("created_at", "tenant__name", "event_type", "event_data")
        )
        events = []
        for e in events_qs:
            events.append({
                "created_at": e["created_at"].strftime("%Y-%m-%d %H:%M") if e["created_at"] else "",
                "tenant": e["tenant__name"] or "—",
                "event_type": e["event_type"],
                "description": (
                    (e.get("event_data") or {}).get("description")
                    or e["event_type"].replace("_", " ").capitalize()
                ),
            })

        # ── Top consumo ──────────────────────────────────────
        top_usage = list(
            UsageMetrics.objects.filter(year=now.year, month=now.month)
            .select_related("tenant")
            .order_by("-eosda_requests")[:10]
            .values(
                "tenant__name", "eosda_requests", "hectares_used",
                "parcels_count", "users_count",
            )
        )

        usage_totals = UsageMetrics.objects.filter(
            year=now.year, month=now.month
        ).aggregate(
            total_users=Sum("users_count"),
            total_parcels=Sum("parcels_count"),
            total_requests=Sum("eosda_requests"),
        )
        total_users = usage_totals["total_users"] or 0
        total_parcels = usage_totals["total_parcels"] or 0
        total_requests = usage_totals["total_requests"] or 0

        # ── Facturas recientes ───────────────────────────────
        recent_invoices = []
        for inv in Invoice.objects.select_related(
            "tenant", "subscription__plan"
        ).order_by("-invoice_date")[:20]:
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

        # ── Tasa de conversión free → pago ───────────────────
        free_total = subs.filter(plan__tier="free").count()
        paid_total = subs.filter(status="active", plan__tier__in=["basic", "pro", "enterprise"]).count()
        conversion_rate = round((paid_total / max(free_total + paid_total, 1)) * 100, 1)

        return Response({
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
                "total_eosda_requests": total_requests,
                "conversion_rate": conversion_rate,
                "free_tenants": free_total,
                "paid_tenants": paid_total,
            },
            "revenue_history": revenue_history,
            "by_plan": by_plan,
            "recent_events": events,
            "top_usage": top_usage,
            "recent_invoices": recent_invoices,
        })


# ═══════════════════════════════════════════════════════════════
#  LISTA DE TENANTS
# ═══════════════════════════════════════════════════════════════

class StaffTenantsAPI(APIView):
    """
    Lista todos los clientes con filtros y paginación simple.
    ?search=nombre&status=active&tier=pro&page=1&page_size=25
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser, StaffAccessPermission]

    def get(self, request):
        qs = (
            Client.objects.exclude(schema_name="public")
            .select_related("subscription__plan")
            .order_by("-created_on")
        )

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(schema_name__icontains=search)
            )

        status_filter = request.query_params.get("status", "")
        if status_filter:
            qs = qs.filter(subscription__status=status_filter)

        tier_filter = request.query_params.get("tier", "")
        if tier_filter:
            qs = qs.filter(subscription__plan__tier=tier_filter)

        now = timezone.now()
        data = [_tenant_summary(t, now) for t in qs]

        return Response({"tenants": data, "total": len(data)})


# ═══════════════════════════════════════════════════════════════
#  DETALLE DE TENANT
# ═══════════════════════════════════════════════════════════════

class StaffTenantDetailAPI(APIView):
    """
    Vista completa de un solo cliente:
    - resumen de suscripción + métricas
    - historial de facturas (últimas 12)
    - historial de consumo (últimos 6 meses)
    - eventos recientes (últimos 20)
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser, StaffAccessPermission]

    def get(self, request, tenant_id):
        tenant = get_object_or_404(Client.objects.exclude(schema_name="public"), pk=tenant_id)
        now = timezone.now()

        # ── Resumen ──────────────────────────────────────────
        summary = _tenant_summary(tenant, now)

        # ── Facturas ─────────────────────────────────────────
        invoices = []
        for inv in Invoice.objects.filter(tenant=tenant).order_by("-invoice_date")[:12]:
            invoices.append({
                "invoice_number": inv.invoice_number,
                "amount": float(inv.total),
                "currency": inv.currency,
                "status": inv.status,
                "invoice_date": inv.invoice_date.strftime("%Y-%m-%d") if inv.invoice_date else None,
                "paid_at": inv.paid_at.strftime("%Y-%m-%d") if inv.paid_at else None,
                "due_date": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else None,
            })

        # ── Consumo histórico (últimos 6 meses) ──────────────
        usage_history = []
        for i in range(5, -1, -1):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            usage = UsageMetrics.objects.filter(tenant=tenant, year=y, month=m).first()
            usage_history.append({
                "year": y,
                "month": m,
                "label": date(y, m, 1).strftime("%b %Y"),
                "eosda_requests": usage.eosda_requests if usage else 0,
                "hectares_used": float(usage.hectares_used) if usage else 0,
                "parcels_count": usage.parcels_count if usage else 0,
                "users_count": usage.users_count if usage else 0,
            })

        # ── Eventos recientes ─────────────────────────────────
        events = []
        for e in BillingEvent.objects.filter(tenant=tenant).order_by("-created_at")[:20]:
            events.append({
                "created_at": e.created_at.strftime("%Y-%m-%d %H:%M"),
                "event_type": e.event_type,
                "data": e.event_data,
            })

        # ── Datos de suscripción (detalle) ────────────────────
        sub = getattr(tenant, "subscription", None)
        sub_detail = None
        if sub:
            sub_detail = {
                "id": sub.id,
                "plan": sub.plan.name if sub.plan else "—",
                "tier": sub.plan.tier if sub.plan else "—",
                "status": sub.status,
                "payment_gateway": sub.payment_gateway,
                "auto_renew": sub.auto_renew,
                "current_period_start": sub.current_period_start.strftime("%Y-%m-%d") if sub.current_period_start else None,
                "current_period_end": sub.current_period_end.strftime("%Y-%m-%d") if sub.current_period_end else None,
                "trial_end": sub.trial_end.strftime("%Y-%m-%d") if sub.trial_end else None,
                "created_at": sub.created_at.strftime("%Y-%m-%d") if hasattr(sub, "created_at") and sub.created_at else None,
            }

        return Response({
            "tenant": summary,
            "subscription": sub_detail,
            "invoices": invoices,
            "usage_history": usage_history,
            "events": events,
        })


# ═══════════════════════════════════════════════════════════════
#  ACCIONES SOBRE TENANTS
# ═══════════════════════════════════════════════════════════════

class StaffTenantActionsAPI(APIView):
    """Suspender, reactivar o cambiar plan de un tenant."""
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser, StaffAccessPermission]

    def post(self, request, tenant_id, action):
        tenant = get_object_or_404(Client.objects.exclude(schema_name="public"), pk=tenant_id)
        sub = getattr(tenant, "subscription", None)

        if action == "suspend":
            if not sub:
                return Response({"error": "Sin suscripción"}, status=400)
            sub.status = "canceled"
            sub.auto_renew = False
            sub.save()
            BillingEvent.objects.create(
                tenant=tenant, subscription=sub, event_type="tenant.suspended",
                event_data={"reason": request.data.get("reason", "Manual por operador")},
            )
            return Response({"status": "canceled", "message": f"Tenant {tenant.name} suspendido."})

        elif action == "activate":
            if not sub:
                return Response({"error": "Sin suscripción"}, status=400)
            sub.status = "active"
            sub.current_period_end = timezone.now() + timedelta(days=30)
            sub.save()
            BillingEvent.objects.create(
                tenant=tenant, subscription=sub, event_type="tenant.reactivated",
                event_data={"message": "Reactivado manualmente por operador"},
            )
            return Response({"status": "active", "message": f"Tenant {tenant.name} reactivado."})

        elif action == "change-plan":
            new_tier = request.data.get("tier")
            if not new_tier or new_tier not in dict(Plan.TIER_CHOICES):
                return Response(
                    {"error": "tier inválido", "valid": list(dict(Plan.TIER_CHOICES).keys())},
                    status=400,
                )
            plan = get_object_or_404(Plan, tier=new_tier, is_active=True)
            if not sub:
                sub = Subscription.objects.create(
                    tenant=tenant, plan=plan, payment_gateway="manual",
                    status="active",
                    current_period_start=timezone.now(),
                    current_period_end=timezone.now() + timedelta(days=30),
                )
            else:
                old_plan = sub.plan.name if sub.plan else "—"
                sub.plan = plan
                sub.save()
            BillingEvent.objects.create(
                tenant=tenant, subscription=sub, event_type="plan.changed",
                event_data={
                    "old_plan": old_plan if "old_plan" in dir() else "none",
                    "new_plan": plan.name,
                    "by": request.user.username,
                },
            )
            return Response({
                "tier": plan.tier, "plan": plan.name,
                "message": f"Plan de {tenant.name} cambiado a {plan.name}.",
            })

        return Response({"error": f"Acción '{action}' no reconocida"}, status=400)


# ═══════════════════════════════════════════════════════════════
#  FINANCIERO
# ═══════════════════════════════════════════════════════════════

class StaffFinancialsAPI(APIView):
    """
    Dashboard financiero detallado.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser, StaffAccessPermission]

    def get(self, request):
        now = timezone.now()

        # ── Facturas pagadas por mes (últimos 12 meses) ──────
        monthly = []
        for i in range(11, -1, -1):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            m_start, m_end = _month_range(y, m)
            invoices = Invoice.objects.filter(status="paid", paid_at__gte=m_start, paid_at__lte=m_end)
            total = invoices.aggregate(t=Sum("total"))["t"] or Decimal("0")
            count = invoices.count()
            monthly.append({
                "year": y, "month": m,
                "label": date(y, m, 1).strftime("%b %Y"),
                "revenue": float(total),
                "invoice_count": count,
            })

        # ── Revenue por plan ──────────────────────────────────
        revenue_by_plan = [
            {
                "plan": row["subscription__plan__name"],
                "tier": row["subscription__plan__tier"],
                "revenue": float(row["total_revenue"]),
                "invoices": row["invoice_count"],
            }
            for row in Invoice.objects.filter(status="paid")
            .values("subscription__plan__name", "subscription__plan__tier")
            .annotate(total_revenue=Sum("total"), invoice_count=Count("id"))
            .order_by("-total_revenue")
        ]

        # ── Próximos cobros (subscriptions activas con periodo) ──
        upcoming = []
        for sub in Subscription.objects.filter(status="active", auto_renew=True).select_related("tenant", "plan").order_by("current_period_end")[:20]:
            upcoming.append({
                "tenant": sub.tenant.name if sub.tenant else "—",
                "plan": sub.plan.name if sub.plan else "—",
                "amount": float(sub.plan.price_cop) if sub.plan else 0,
                "next_renewal": sub.current_period_end.strftime("%Y-%m-%d") if sub.current_period_end else None,
                "gateway": sub.payment_gateway,
            })

        return Response({
            "monthly_revenue": monthly,
            "revenue_by_plan": revenue_by_plan,
            "upcoming_renewals": upcoming,
            "total_revenue_12m": float(sum(m["revenue"] for m in monthly)),
        })
