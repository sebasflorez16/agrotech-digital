"""
Tests unitarios para el modelo User.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestUserModel:
    """Tests para el modelo personalizado de Usuario."""

    def test_create_user(self):
        """Test creación básica de usuario."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            name="Test",
            last_name="User"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.name == "Test"
        assert user.last_name == "User"
        assert user.check_password("testpass123")
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self):
        """Test creación de superusuario."""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )
        assert admin.is_staff
        assert admin.is_superuser
        assert admin.is_active

    def test_user_full_name(self):
        """Test método get_full_name."""
        user = User.objects.create_user(
            username="john",
            name="John",
            last_name="Doe"
        )
        assert user.get_full_name() == "John Doe"

    def test_user_short_name(self):
        """Test método get_short_name."""
        user = User.objects.create_user(
            username="john",
            name="John"
        )
        assert user.get_short_name() == "John"

    def test_user_str_representation(self):
        """Test representación string del usuario."""
        user = User.objects.create_user(
            username="testuser",
            name="Test",
            last_name="User"
        )
        assert str(user) == "Test User"

    def test_unique_username(self):
        """Test que username debe ser único."""
        User.objects.create_user(username="testuser", email="test1@example.com")
        with pytest.raises(IntegrityError):
            User.objects.create_user(username="testuser", email="test2@example.com")

    def test_unique_email(self):
        """Test que email debe ser único."""
        User.objects.create_user(username="user1", email="test@example.com")
        with pytest.raises(IntegrityError):
            User.objects.create_user(username="user2", email="test@example.com")

    def test_user_roles(self):
        """Test asignación de roles."""
        admin = User.objects.create_user(username="admin", role="admin")
        manager = User.objects.create_user(username="manager", role="manager")
        employee = User.objects.create_user(username="employee", role="employee")
        accountant = User.objects.create_user(username="accountant", role="accountant")

        assert admin.role == "admin"
        assert manager.role == "manager"
        assert employee.role == "employee"
        assert accountant.role == "accountant"

    def test_user_reports_to_hierarchy(self):
        """Test jerarquía de reportes (manager -> employee)."""
        manager = User.objects.create_user(username="manager", name="Manager")
        employee = User.objects.create_user(
            username="employee",
            name="Employee",
            reports_to=manager
        )
        assert employee.reports_to == manager
        assert manager in employee.reports_to.user_set.all()

    def test_user_contract_types(self):
        """Test tipos de contrato."""
        indefinido = User.objects.create_user(
            username="user1",
            contract_type="indefinido"
        )
        fijo = User.objects.create_user(
            username="user2",
            contract_type="fijo"
        )
        obra_labor = User.objects.create_user(
            username="user3",
            contract_type="obra_labor"
        )

        assert indefinido.contract_type == "indefinido"
        assert fijo.contract_type == "fijo"
        assert obra_labor.contract_type == "obra_labor"

    def test_user_banking_info(self):
        """Test información bancaria del usuario."""
        user = User.objects.create_user(
            username="employee",
            bank_name="Bancolombia",
            account_number="1234567890",
            account_type="ahorros"
        )
        assert user.bank_name == "Bancolombia"
        assert user.account_number == "1234567890"
        assert user.account_type == "ahorros"

    def test_user_salary_and_dates(self):
        """Test salario y fechas laborales."""
        from datetime import date
        user = User.objects.create_user(
            username="employee",
            salary=3000000,
            hire_date=date(2024, 1, 1)
        )
        assert user.salary == 3000000
        assert user.hire_date == date(2024, 1, 1)

    def test_user_contact_info(self):
        """Test información de contacto."""
        user = User.objects.create_user(
            username="employee",
            phone="+573001234567",
            address="Calle 123 #45-67, Bogotá"
        )
        assert user.phone == "+573001234567"
        assert user.address == "Calle 123 #45-67, Bogotá"

    def test_user_historical_records(self):
        """Test que se registra el historial de cambios."""
        user = User.objects.create_user(username="testuser", name="Test")
        assert user.history.count() == 1
        
        user.name = "Updated Test"
        user.save()
        assert user.history.count() == 2
        
        # Verificar cambio histórico
        latest = user.history.first()
        assert latest.name == "Updated Test"
