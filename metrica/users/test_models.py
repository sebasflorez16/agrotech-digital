"""
Tests unitarios para el modelo User.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

pytestmark = pytest.mark.django_db


def _create(**extra):
    username = extra.pop("username", "testuser")
    base = {
        "username": username,
        "email": extra.pop("email", f"{username}@example.com"),
        "name": extra.pop("name", "Test"),
        "last_name": extra.pop("last_name", "User"),
        "password": extra.pop("password", "testpass123"),
    }
    base.update(extra)
    return User.objects.create_user(**base)


class TestUserModel:
    """Tests para el modelo personalizado de Usuario."""

    def test_create_user(self):
        user = _create(username="testuser", email="test@example.com")
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.name == "Test"
        assert user.last_name == "User"
        assert user.check_password("testpass123")
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            name="Admin",
            last_name="User",
        )
        assert admin.is_staff
        assert admin.is_superuser
        assert admin.is_active

    def test_user_full_name(self):
        user = _create(username="john", name="John", last_name="Doe")
        assert str(user) == "John Doe"

    def test_user_short_name(self):
        user = _create(username="john", name="John")
        assert user.name == "John"

    def test_user_str_representation(self):
        user = _create(username="testuser", name="Test", last_name="User")
        assert str(user) == "Test User"

    def test_unique_username(self):
        _create(username="testuser", email="test1@example.com")
        with pytest.raises(IntegrityError):
            _create(username="testuser", email="test2@example.com")

    def test_unique_email(self):
        _create(username="user1", email="test@example.com")
        with pytest.raises(IntegrityError):
            _create(username="user2", email="test@example.com")

    def test_user_roles(self):
        admin = _create(username="admin", role="admin")
        manager = _create(username="manager", role="manager")
        employee = _create(username="employee", role="employee")
        accountant = _create(username="accountant", role="accountant")

        assert admin.role == "admin"
        assert manager.role == "manager"
        assert employee.role == "employee"
        assert accountant.role == "accountant"

    def test_user_reports_to_hierarchy(self):
        manager = _create(username="manager", name="Manager")
        employee = _create(username="employee", name="Employee", reports_to=manager)
        assert employee.reports_to == manager

    def test_user_contract_types(self):
        indefinido = _create(username="user1", contract_type="indefinido")
        fijo = _create(username="user2", contract_type="fijo")
        obra_labor = _create(username="user3", contract_type="obra_labor")

        assert indefinido.contract_type == "indefinido"
        assert fijo.contract_type == "fijo"
        assert obra_labor.contract_type == "obra_labor"

    def test_user_banking_info(self):
        user = _create(
            username="employee",
            bank_name="Bancolombia",
            account_number="1234567890",
            account_type="ahorros",
        )
        assert user.bank_name == "Bancolombia"
        assert user.account_number == "1234567890"
        assert user.account_type == "ahorros"

    def test_user_salary_and_dates(self):
        from datetime import date
        user = _create(
            username="employee",
            salary=3000000,
            hire_date=date(2024, 1, 1),
        )
        assert user.salary == 3000000
        assert user.hire_date == date(2024, 1, 1)

    def test_user_contact_info(self):
        user = _create(
            username="employee",
            phone="+573001234567",
            address="Calle 123 #45-67, Bogotá",
        )
        assert user.phone == "+573001234567"
        assert user.address == "Calle 123 #45-67, Bogotá"

    def test_user_historical_records(self):
        user = _create(username="testuser", name="Test")
        assert user.historical.count() == 1

        user.name = "Updated Test"
        user.save()
        assert user.historical.count() == 2

        latest = user.historical.first()
        assert latest.name == "Updated Test"
