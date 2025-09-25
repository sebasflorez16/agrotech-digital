from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.views import defaults as default_views


urlpatterns = [
    # 🔹 Autenticación JWT - Solo tu vista custom con CORS
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("api/authentication/", include("authentication.urls", namespace="authentication")),

    # 🔹 Administración (Solo para backoffice)
    path("admin/", admin.site.urls),

    # 🔹 APIs principales del sistema
    path("users/api/", include("metrica.users.routers")),
    path("api/RRHH/", include("RRHH.routers")),         # Recursos Humanos para posiciones y departamentos
    path("api/parcels/", include("parcels.urls")),  # Endpoints personalizados/proxy EOSDA bajo /api/parcels/ (¡PRIMERO para evitar que el router tape rutas manuales!)
    path("api/parcels/", include("parcels.routers", namespace="parcels")),# Gestión de parcelas
    path("api/labores/", include("labores.routers", namespace="labores")),  # Gestión de labores agrícolas
    path("api/inventario/", include("inventario.routers")),  # Gestión de inventario y almacenes
    path("api/crop/", include("crop.routers", namespace="crop")),  # Gestión de cultivos

    # 🔹 Allauth (para admin si es necesario)
    path("accounts/", include("allauth.urls")),

    # 🔹 Recarga en desarrollo (solo para DEBUG)
    path("__reload__/", include("django_browser_reload.urls")),
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
