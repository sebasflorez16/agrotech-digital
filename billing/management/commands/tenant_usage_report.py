"""
Reporte de tenants y consumo para diagnóstico de producción.

Muestra:
  1. Tenants (más recientes primero) con plan, estado, consumo del mes.
  2. Consumo global (EosdaRequestLog) por operación y por tenant.
  3. Últimos requests registrados.

Uso:
    python manage.py tenant_usage_report
    python manage.py tenant_usage_report --limit 30
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count


class Command(BaseCommand):
    help = 'Reporte de tenants y consumo (diagnóstico de producción)'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=20, help='Número de tenants a mostrar')
        parser.add_argument('--recent', type=int, default=20, help='Número de requests recientes a mostrar')

    def handle(self, *args, **options):
        from base_agrotech.models import Client
        from billing.models import UsageMetrics, EosdaRequestLog, Subscription

        limit = options['limit']
        recent = options['recent']
        now = timezone.now()

        self.stdout.write(self.style.WARNING('=' * 100))
        self.stdout.write(self.style.WARNING('TENANTS (más recientes primero)'))
        self.stdout.write(self.style.WARNING('=' * 100))

        tenants = Client.objects.exclude(schema_name='public').order_by('-created_on')[:limit]
        self.stdout.write(
            f"{'Creado':10} | {'schema':28} | {'nombre':28} | "
            f"{'plan':10} | {'estado':14} | {'reqs/mes':>8} | {'ha':>7} | {'parc':>5} | {'users':>5}"
        )
        for t in tenants:
            sub = Subscription.objects.filter(tenant=t).first()
            plan = sub.plan.tier if sub and sub.plan else '?'
            status = sub.status if sub else 'sin-sub'
            metrics = UsageMetrics.objects.filter(tenant=t, year=now.year, month=now.month).first()
            reqs = metrics.eosda_requests if metrics else 0
            ha = round(metrics.hectares_used, 2) if metrics else 0
            parcels = metrics.parcels_count if metrics else 0
            users = metrics.users_count if metrics else 0
            self.stdout.write(
                f"{t.created_on.strftime('%Y-%m-%d'):10} | {t.schema_name:28} | {t.name:28} | "
                f"{plan:10} | {status:14} | {reqs:>8} | {ha:>7} | {parcels:>5} | {users:>5}"
            )

        total_tenants = Client.objects.exclude(schema_name='public').count()
        self.stdout.write(f"\nTotal tenants (sin public): {total_tenants}")

        self.stdout.write('\n' + self.style.WARNING('=' * 100))
        self.stdout.write(self.style.WARNING('CONSUMO GLOBAL (EosdaRequestLog) — por operación'))
        self.stdout.write(self.style.WARNING('=' * 100))
        for row in EosdaRequestLog.objects.values('operation').annotate(n=Count('id')).order_by('-n'):
            self.stdout.write(f"  {row['operation'] or '-':25} | {row['n']:>6} requests")

        self.stdout.write('\n' + self.style.WARNING('CONSUMO GLOBAL — por tenant (top 15)'))
        self.stdout.write(self.style.WARNING('=' * 100))
        for row in EosdaRequestLog.objects.values('tenant__schema_name').annotate(n=Count('id')).order_by('-n')[:15]:
            self.stdout.write(f"  {row['tenant__schema_name']:28} | {row['n']:>6} requests")

        self.stdout.write('\n' + self.style.WARNING(f'ÚLTIMOS {recent} REQUESTS'))
        self.stdout.write(self.style.WARNING('=' * 100))
        for r in EosdaRequestLog.objects.select_related('tenant').order_by('-created_at')[:recent]:
            self.stdout.write(
                f"  {r.created_at.strftime('%Y-%m-%d %H:%M')} | {r.tenant.schema_name:20} | "
                f"{r.operation or '-':20} | {r.index_type or '-':6} | parcela={r.parcel_id or '-':8} | {r.source}"
            )

        self.stdout.write('\n' + self.style.SUCCESS('✅ Reporte completado'))
