from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from .forms import UserCreationForm, UserUpdateForm
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView, CreateView, ListView
from users.serializers import UserProfileUtilSerializer
from rest_framework.response import Response
from django.contrib import messages
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class TenantAdminRequiredMixin(UserPassesTestMixin):
    """
    Restringe la gestión de usuarios del tenant a roles admin/manager.

    Evita que cualquier usuario autenticado (employee/accountant) administre
    a otros usuarios del tenant.
    """
    raise_exception = False

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        # El superusuario global (staff) puede administrar todo.
        if user.is_superuser:
            return True
        return getattr(user, 'role', None) in ('admin', 'manager')


class UsersListView(LoginRequiredMixin, TenantAdminRequiredMixin, ListView):
    model = User
    template_name = "apps/hospital/staff/all-staff.html"
    context_object_name = "users_list"

    def get_queryset(self):
        # Aislar por tenant: solo usuarios de la organización actual.
        tenant = getattr(self.request, 'tenant', None)
        qs = User.objects.all()
        if tenant is not None and getattr(tenant, 'schema_name', 'public') != 'public':
            qs = qs.filter(tenant_id=tenant.id)
        return qs

class UserCreateView(LoginRequiredMixin, TenantAdminRequiredMixin, SuccessMessageMixin, CreateView):
    def get(self, request):
        form = UserCreationForm()
        return render(request, 'apps/hospital/staff/member.html', {'form': form})

    def _check_users_limit(self, request):
        """
        Verifica si el tenant puede crear más usuarios según su plan.
        Returns: (is_allowed, error_message)
        """
        try:
            from billing.models import Subscription
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return True, None  # Sin tenant, no restringir
            
            subscription = getattr(tenant, 'subscription', None)
            if not subscription:
                # Intentar obtener la suscripción directamente
                try:
                    subscription = Subscription.objects.get(tenant=tenant)
                except Subscription.DoesNotExist:
                    return True, None  # Sin suscripción, no restringir
            
            current_users = User.objects.filter(tenant_id=tenant.id).count()
            is_within, limit = subscription.check_limit('users', current_users + 1)
            
            if not is_within:
                logger.warning(
                    f"Límite de usuarios excedido: tenant={tenant.name}, "
                    f"current={current_users}, limit={limit}, plan={subscription.plan.name}"
                )
                return False, (
                    f'Tu plan {subscription.plan.name} permite hasta {limit} usuario(s). '
                    f'Actualmente tienes {current_users}. '
                    f'Mejora tu plan para agregar más usuarios.'
                )
            return True, None
        except Exception as e:
            logger.error(f"Error verificando límite de usuarios: {e}")
            return True, None  # En caso de error, no bloquear
    
    def post(self, request, *args, **kwargs):
        # Verificar límite de usuarios antes de crear
        is_allowed, error_msg = self._check_users_limit(request)
        if not is_allowed:
            form = UserCreationForm(request.POST, request.FILES)
            messages.error(request, error_msg)
            return render(request, 'apps/hospital/staff/member.html', {
                'form': form,
                'users_limit_error': error_msg,
            })
        
        form = UserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            # Asignar el tenant actual (aislamiento multi-tenant).
            tenant = getattr(request, 'tenant', None)
            if tenant is not None and getattr(tenant, 'schema_name', 'public') != 'public':
                user.tenant = tenant
            user.save()
            username = form.cleaned_data.get("username")
            logger.info(f"Usuario creado: {username} (tenant={getattr(tenant, 'schema_name', 'public')})")
            messages.success(request, f"Usuario '{username}' creado correctamente.")
            return redirect("users:users-all")
        else:
            return render(request, 'apps/hospital/staff/member.html', {'form': form})
        
class UserDetailView(LoginRequiredMixin, TenantAdminRequiredMixin, DetailView):
    model = User
    template_name = "apps/hospital/staff/profile.html"
    context_object_name = "user"

    def get_object(self):
        tenant = getattr(self.request, 'tenant', None)
        qs = self.model.objects.all()
        if tenant is not None and getattr(tenant, 'schema_name', 'public') != 'public':
            qs = qs.filter(tenant_id=tenant.id)
        return get_object_or_404(qs, pk=self.kwargs['pk'])

class UserUpdateView(LoginRequiredMixin, TenantAdminRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "apps/hospital/staff/edit-member.html"
    success_url = reverse_lazy('users:users-all')

    def get_object(self):
        tenant = getattr(self.request, 'tenant', None)
        qs = self.model.objects.all()
        if tenant is not None and getattr(tenant, 'schema_name', 'public') != 'public':
            qs = qs.filter(tenant_id=tenant.id)
        return get_object_or_404(qs, pk=self.kwargs['pk']) #Filtramos el usuario
    

class UserProfileUtil(viewsets.ModelViewSet):
    def get_queryset(self):
        # Filtrar para devolver solo los datos del usuario autenticado
        return User.objects.filter(id=self.request.user.id)

    serializer_class = UserProfileUtilSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']  # Solo permitir GET para este endpoint

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)