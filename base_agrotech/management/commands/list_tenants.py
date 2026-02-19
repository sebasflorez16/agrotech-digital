"""
Comando para listar todos los tenants existentes
"""
from django.core.management.base import BaseCommand
from base_agrotech.models import Client, Domain
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from django.db import connection

User = get_user_model()

class Command(BaseCommand):
    help = 'Listar todos los tenants y sus dominios'

    def add_arguments(self, parser):
        parser.add_argument('--detailed', action='store_true', help='Mostrar información detallada')

    def handle(self, *args, **options):
        detailed = options['detailed']
        
        self.stdout.write("=" * 70)
        self.stdout.write("🏢 LISTA DE TENANTS")
        self.stdout.write("=" * 70)
        
        tenants = Client.objects.all().order_by('schema_name')
        
        if not tenants.exists():
            self.stdout.write("❌ No hay tenants creados")
            return
        
        for tenant in tenants:
            self.stdout.write(f"\n📋 TENANT: {tenant.name}")
            self.stdout.write(f"   Schema: {tenant.schema_name}")
            self.stdout.write(f"   ID: {tenant.id}")
            if hasattr(tenant, 'created_on'):
                self.stdout.write(f"   Creado: {tenant.created_on}")
            if hasattr(tenant, 'paid_until') and tenant.paid_until:
                self.stdout.write(f"   Pagado hasta: {tenant.paid_until}")
            if hasattr(tenant, 'on_trial'):
                self.stdout.write(f"   En trial: {'Sí' if tenant.on_trial else 'No'}")
            
            # Verificar suscripción
            try:
                sub = tenant.subscription
                self.stdout.write(f"   💳 Suscripción: {sub.plan.name} ({sub.status})")
            except Exception:
                self.stdout.write(f"   ⚠️ Sin suscripción")
            
            # Mostrar dominios
            domains = Domain.objects.filter(tenant=tenant)
            self.stdout.write("   🌐 Dominios:")
            for domain in domains:
                status = "🔹 Primario" if domain.is_primary else "🔸 Secundario"
                self.stdout.write(f"      {status} {domain.domain}")
            
            # Información detallada
            if detailed:
                try:
                    # Verificar que el schema existe
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT schema_name FROM information_schema.schemata 
                            WHERE schema_name = %s
                        """, [tenant.schema_name])
                        schema_exists = cursor.fetchone() is not None
                    
                    if schema_exists:
                        with schema_context(tenant.schema_name):
                            try:
                                user_count = User.objects.count()
                                admin_count = User.objects.filter(is_superuser=True).count()
                                self.stdout.write(f"   👥 Usuarios: {user_count} (Admins: {admin_count})")
                                
                                if admin_count > 0:
                                    admins = User.objects.filter(is_superuser=True)[:3]
                                    for admin in admins:
                                        self.stdout.write(f"      👤 {admin.username} ({admin.email})")
                            except Exception as e:
                                self.stdout.write(f"   ⚠️ Error accediendo a usuarios: {e}")
                    else:
                        self.stdout.write(f"   ⚠️ Schema '{tenant.schema_name}' no existe en la base de datos")
                        
                except Exception as e:
                    self.stdout.write(f"   ⚠️ Error accediendo al schema: {e}")
            
            self.stdout.write("-" * 50)
        
        self.stdout.write(f"\n📊 Total de tenants: {tenants.count()}")
        self.stdout.write("=" * 70)
