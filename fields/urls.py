from django.urls import path
from .views import FieldView

app_name = 'fields'

urlpatterns = [
    path('', FieldView.as_view(), name='fields'),
]

