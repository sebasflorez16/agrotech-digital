#!/bin/bash

# Script para ejecutar todos los tests con diferentes configuraciones
# Uso: bash scripts/run_tests.sh [--quick|--full|--coverage]

set -e  # Exit on error

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 AgroTech Digital - Test Suite${NC}\n"

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Error: Ejecutar desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Configurar variables de entorno para tests
export DJANGO_SETTINGS_MODULE=config.settings.local
export DJANGO_SECRET_KEY=test-secret-key

# Función para tests rápidos
run_quick_tests() {
    echo -e "${YELLOW}⚡ Ejecutando tests rápidos (sin integración)...${NC}\n"
    pytest -v -m "not slow and not eosda" --tb=short
}

# Función para tests completos
run_full_tests() {
    echo -e "${YELLOW}🔬 Ejecutando suite completa de tests...${NC}\n"
    pytest -v --tb=short
}

# Función para tests con coverage
run_coverage_tests() {
    echo -e "${YELLOW}📊 Ejecutando tests con coverage...${NC}\n"
    pytest -v --cov=. --cov-report=html --cov-report=term-missing --cov-report=xml
    echo -e "\n${GREEN}✅ Reporte de coverage generado en: htmlcov/index.html${NC}"
}

# Función para tests específicos
run_specific_tests() {
    echo -e "${YELLOW}🎯 Ejecutando tests de: $1${NC}\n"
    pytest -v "$1" --tb=short
}

# Linting y code quality
run_linting() {
    echo -e "${YELLOW}🔍 Ejecutando linting...${NC}\n"
    
    echo "- flake8..."
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true
    
    echo -e "\n- black (check)..."
    black --check --diff . || true
    
    echo -e "\n- isort (check)..."
    isort --check-only --diff . || true
}

# Parse argumentos
case "${1:-}" in
    --quick|-q)
        run_quick_tests
        ;;
    --full|-f)
        run_full_tests
        ;;
    --coverage|-c)
        run_coverage_tests
        ;;
    --lint|-l)
        run_linting
        ;;
    --all|-a)
        run_linting
        run_coverage_tests
        ;;
    --help|-h)
        echo "Uso: bash scripts/run_tests.sh [opción]"
        echo ""
        echo "Opciones:"
        echo "  --quick, -q      Tests rápidos (sin integración)"
        echo "  --full, -f       Suite completa de tests"
        echo "  --coverage, -c   Tests con reporte de coverage"
        echo "  --lint, -l       Solo linting (flake8, black, isort)"
        echo "  --all, -a        Linting + coverage (CI completo)"
        echo "  --help, -h       Mostrar esta ayuda"
        echo ""
        echo "Ejemplos:"
        echo "  bash scripts/run_tests.sh --quick"
        echo "  bash scripts/run_tests.sh --coverage"
        echo "  pytest parcels/test_models.py  # Test específico"
        ;;
    "")
        # Sin argumentos, ejecutar tests rápidos
        run_quick_tests
        ;;
    *)
        # Argumento desconocido, tratar como path de test específico
        run_specific_tests "$1"
        ;;
esac

echo -e "\n${GREEN}✅ Tests completados${NC}"
