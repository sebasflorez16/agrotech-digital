from django.urls import path
from . import views
app_name = "parcels"


from .proxy import eosda_wmts_proxy

urlpatterns = [
## Eliminado: vista dashboard que no existe
    path('eosda-wmts-tile/', eosda_wmts_proxy, name='eosda_wmts_proxy'),
    # Endpoints alineados con el nuevo flujo EOSDA
path('eosda-scenes/', views.EosdaScenesView.as_view(), name='eosda_scenes'),
path('eosda-image/', views.EosdaImageView.as_view(), name='eosda_image'),
path('eosda-image-result/', views.EosdaImageResultView.as_view(), name='eosda_image_result'),
]
