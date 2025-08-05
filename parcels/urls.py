from django.urls import path
from . import views
app_name = "parcels"


from .proxy import eosda_wmts_proxy
from .eosda_search import eosda_search

urlpatterns = [
    path('dashboard/', views.parcels_dashboard, name='dashboard'),
    path('eosda-wmts-urls/', views.eosda_wmts_urls, name='eosda_wmts_urls'),
    # Endpoint proxy para tiles WMTS de EOSDA (evita CORS y protege el token)
    # Recibe los parámetros de tile y devuelve la imagen directamente al frontend
    path('eosda-wmts-tile/', eosda_wmts_proxy, name='eosda_wmts_proxy'),
    # Endpoint profesional para búsqueda de escenas satelitales EOSDA
    path('eosda-search/', eosda_search, name='eosda_search'),
]
