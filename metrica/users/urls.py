from django.urls import path
from rest_framework.routers import DefaultRouter
from metrica.users.views import (
    UserCreateView, UsersListView, UserDetailView, UserUpdateView
)
from metrica.users.api_verify_password import VerifyPasswordView

app_name = "users"

urlpatterns = [
    path("all/", UsersListView.as_view(), name="users-all"),
    path("create/", UserCreateView.as_view(), name="users-create"),
    path("detail/<str:pk>/", UserDetailView.as_view(), name="users-detail"),
    path("edit/<int:pk>/", UserUpdateView.as_view(), name="users-edit"),
    path("api/verificar-password/", VerifyPasswordView.as_view(), name="api-verificar-password"),
]
