from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.views import defaults as default_views

urlpatterns = [

    # 🔹 Autenticación y Tokens JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("api/auth/", include("authentication.urls", namespace="authentication")),

    # 🔹 Administración
    path("admin/", admin.site.urls),
    # 🔹 API global
    # path("", include("metrica.api_urls")),

    # 🔹 Gestión de usuarios
    path("users/", include("metrica.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),

    # 🔹 Routers para usuarios
    path("users/api/", include("metrica.users.routers")),
    # los namespaces son importantes para evitar conflictos con el app_name de los routers


    # 🔹 Módulos principales del sistema
    path("api/RRHH/", include("RRHH.routers")),         # Recursos Humanos para posiciones y departamentos
    
    # ✅ ORDEN CRÍTICO: Router DRF PRIMERO (CRUD de parcelas)
    path("api/parcels/", include("parcels.routers")),  # ViewSet con /parcel/, /parcel/<pk>/, etc.
    
    # URLs personalizadas DESPUÉS (analytics, weather, proxy EOSDA)
    path("api/parcels/", include("parcels.urls")),  # Endpoints específicos de EOSDA/Weather
    path("parcels/", include("parcels.urls")),  # Dashboard de parcelas (templates)
    path("api/labores/", include("labores.routers", namespace="labores")),  # Gestión de labores agrícolas
    path("api/inventario/", include("inventario.routers")),  # Gestión de inventario y almacenes
    # Reporte de inventario por almacén (HTML y PDF)
    path("inventario/", include("inventario.urls")),
    path("api/crop/", include("crop.routers", namespace="crop")),  # Gestión de cultivos

    # 🔹 Billing y Suscripciones
    path("billing/", include("billing.urls", namespace="billing")),  # Sistema de facturación

    # 🔹 Interfaz y páginas
    path("pages/", include("pages.urls", namespace="pages")),      # Páginas estáticas
    path("uikit/", include("uikit.urls", namespace="uikit")),      # Componentes UI

    # 🔹 Recarga en desarrollo (solo para DEBUG)
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# 🔹 Modo DEBUG: Manejo de errores y Debug Toolbar
if settings.DEBUG:
    urlpatterns += [
        path("400/", default_views.bad_request, kwargs={"exception": Exception("Bad Request!")}),
        path("403/", default_views.permission_denied, kwargs={"exception": Exception("Permission Denied")}),
        path("404/", default_views.page_not_found, kwargs={"exception": Exception("Page not Found")}),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
