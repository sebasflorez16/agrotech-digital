# Testing Guide - AgroTech Digital

Guía completa de testing para el proyecto AgroTech Digital.

## 📋 Tabla de Contenidos

- [Setup Inicial](#setup-inicial)
- [Ejecutar Tests](#ejecutar-tests)
- [Estructura de Tests](#estructura-de-tests)
- [Writing Tests](#writing-tests)
- [Coverage](#coverage)
- [CI/CD](#cicd)

## 🚀 Setup Inicial

### 1. Instalar Dependencias de Testing

```bash
pip install -r requirements.txt
```

Esto instalará:
- pytest
- pytest-django
- pytest-cov
- pytest-mock
- factory-boy
- faker

### 2. Configurar Variables de Entorno

```bash
export DJANGO_SETTINGS_MODULE=config.settings.local
export DJANGO_SECRET_KEY=test-secret-key
```

### 3. Configurar Base de Datos de Test

Los tests usan SQLite in-memory por defecto (más rápido). Para usar PostgreSQL:

```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/agrotech_test
```

## 🧪 Ejecutar Tests

### Tests Rápidos (recomendado para desarrollo)

```bash
bash scripts/run_tests.sh --quick
# O simplemente:
pytest -m "not slow and not eosda"
```

### Suite Completa

```bash
bash scripts/run_tests.sh --full
# O:
pytest
```

### Con Coverage

```bash
bash scripts/run_tests.sh --coverage
# O:
pytest --cov=. --cov-report=html
```

Luego abre `htmlcov/index.html` en tu navegador.

### Tests Específicos

```bash
# Por archivo
pytest parcels/test_models.py

# Por clase
pytest parcels/test_models.py::TestParcelModel

# Por función
pytest parcels/test_models.py::TestParcelModel::test_create_parcel_basic

# Por marker
pytest -m unit           # Solo tests unitarios
pytest -m integration    # Solo tests de integración
pytest -m eosda          # Solo tests de EOSDA API
```

### Tests en Paralelo (más rápido)

```bash
pytest -n auto  # Usa todos los CPUs disponibles
pytest -n 4     # Usa 4 workers
```

## 📁 Estructura de Tests

```
agrotech-digital/
├── conftest.py                           # Fixtures compartidas
├── pytest.ini                            # Configuración pytest
├── .coveragerc                           # Configuración coverage
│
├── authentication/
│   └── test_auth_multitenant.py         # Tests de autenticación
│
├── parcels/
│   ├── test_models.py                    # Tests unitarios de modelos
│   └── test_eosda_integration.py         # Tests de integración EOSDA
│
├── crop/
│   └── test_models.py                    # Tests de cultivos
│
└── metrica/users/
    └── test_models.py                    # Tests de usuarios
```

## ✍️ Writing Tests

### Ejemplo de Test Unitario

```python
import pytest
from parcels.models import Parcel

pytestmark = pytest.mark.django_db


class TestParcelModel:
    """Tests para el modelo Parcel."""

    def test_create_parcel(self, sample_employee):
        """Test creación básica de parcela."""
        parcel = Parcel.objects.create(
            name="Test Field",
            manager=sample_employee
        )
        assert parcel.name == "Test Field"
        assert parcel.manager == sample_employee
```

### Ejemplo de Test de Integración

```python
import pytest
from unittest.mock import patch, MagicMock

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


class TestEOSDAAPI:
    """Tests de integración con EOSDA."""

    @patch('parcels.views.requests.get')
    def test_scene_search(self, mock_get, authenticated_client, sample_parcel):
        """Test búsqueda de escenas."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'results': []}
        
        response = authenticated_client.post(
            f'/api/parcels/{sample_parcel.pk}/search-scenes/',
            {'start_date': '2024-01-01', 'end_date': '2024-01-31'}
        )
        
        assert response.status_code == 200
```

### Usando Fixtures

Fixtures disponibles en `conftest.py`:

```python
def test_with_fixtures(
    api_client,          # Cliente API no autenticado
    authenticated_client, # Cliente API autenticado
    admin_user,          # Usuario administrador
    regular_user,        # Usuario regular
    sample_employee,     # Empleado de ejemplo
    sample_parcel,       # Parcela de ejemplo
    sample_crop,         # Cultivo de ejemplo
    mock_eosda_response  # Respuesta mock de EOSDA
):
    # Tu test aquí
    pass
```

## 📊 Coverage

### Meta de Coverage

- **Objetivo mínimo**: 70%
- **Objetivo ideal**: 80%+

### Ver Reporte de Coverage

```bash
# Generar reporte
pytest --cov=. --cov-report=html

# Abrir en navegador
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage por Módulo

```bash
pytest --cov=parcels --cov-report=term-missing
```

### Excluir de Coverage

Agregar comentario `# pragma: no cover`:

```python
def debug_function():  # pragma: no cover
    print("Solo para debugging")
```

## 🔄 CI/CD

### GitHub Actions

Los tests se ejecutan automáticamente en cada push/PR:

```yaml
# .github/workflows/ci-cd.yml
- Linting (flake8, black, isort)
- Tests con PostgreSQL
- Coverage report
- Security scan
```

Ver estado en: https://github.com/tu-repo/actions

### Pre-commit Hooks (Opcional)

```bash
# Instalar pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Ejecutar manualmente
pre-commit run --all-files
```

## 🏷️ Markers

Tests organizados por markers:

```ini
[pytest]
markers =
    unit: Tests unitarios
    integration: Tests de integración
    slow: Tests lentos
    eosda: Tests que interactúan con EOSDA API
    tenant: Tests de multi-tenancy
```

Uso:

```bash
pytest -m unit              # Solo unitarios
pytest -m "not slow"        # Excluir lentos
pytest -m "unit or integration"  # Unitarios O integración
```

## 🐛 Debugging Tests

### Ver Output Completo

```bash
pytest -v -s  # -s muestra prints
```

### Detener en Primer Fallo

```bash
pytest -x  # Exit on first failure
```

### Entrar en Debugger

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    # O usar pytest's debugger
    pytest.set_trace()
```

### Ver Warnings

```bash
pytest -v --tb=short --strict-warnings
```

## 📈 Métricas de Tests

### Estado Actual

| Módulo | Tests | Coverage |
|--------|-------|----------|
| authentication | 15+ | TBD |
| parcels | 30+ | TBD |
| crop | 20+ | TBD |
| users | 15+ | TBD |

### Ejecutar Métricas

```bash
pytest --cov=. --cov-report=term-missing
```

## 🔧 Troubleshooting

### Error: "No module named 'pytest'"

```bash
pip install pytest pytest-django
```

### Error: "Database is not configured"

```bash
export DJANGO_SETTINGS_MODULE=config.settings.local
```

### Tests Lentos

```bash
# Usar SQLite en memoria (más rápido)
pytest --reuse-db

# Tests en paralelo
pytest -n auto
```

### Mock Fails

Verificar que estás mockeando el path correcto:

```python
# ❌ Incorrecto
@patch('requests.get')

# ✅ Correcto  
@patch('parcels.views.requests.get')
```

## 📚 Recursos

- [pytest documentation](https://docs.pytest.org/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [Django testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Factory Boy](https://factoryboy.readthedocs.io/)

## 🤝 Contribuir

Al agregar nueva funcionalidad:

1. ✅ Escribir tests ANTES de implementar (TDD)
2. ✅ Mantener coverage > 70%
3. ✅ Usar fixtures existentes
4. ✅ Agregar docstrings a tests
5. ✅ Marcar correctamente (unit/integration/slow)

## 📞 Soporte

¿Problemas con tests? Contacta al equipo de desarrollo.
