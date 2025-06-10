from django.urls import path
from . import views

app_name = "parcels"

urlpatterns = [
    path('dashboard/', views.parcels_dashboard, name='dashboard'),
]
