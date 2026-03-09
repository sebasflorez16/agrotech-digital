from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
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

class UsersListView(LoginRequiredMixin, ListView):
    model = User
    template_name = "apps/hospital/staff/all-staff.html"
    context_object_name = "users_list" 

    

class UserCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
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
            
            current_users = User.objects.count()
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
            form.save()
            username = form.cleaned_data.get("username")
            return redirect("users:users-all")
        else:
            return render(request, 'apps/hospital/staff/member.html', {'form': form})
        
class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "apps/hospital/staff/profile.html"
    context_object_name = "user"

    def get_object(self):
        return get_object_or_404(self.model, pk=self.kwargs['pk'])

class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "apps/hospital/staff/edit-member.html"
    success_url = reverse_lazy('users:users-all')

    def get_object(self):
        return get_object_or_404(self.model, pk=self.kwargs['pk']) #Filtramos el usuario
    

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