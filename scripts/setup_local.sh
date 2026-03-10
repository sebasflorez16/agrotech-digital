#!/bin/bash

# Script de setup completo para desarrollo local
# Uso: bash scripts/setup_local.sh

set -e  # Exit on error

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════╗"
echo "║   AgroTech Digital - Setup Desarrollo Local  ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Error: Ejecutar desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# 1. Verificar Python
echo -e "${YELLOW}🐍 Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no está instalado${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✅ $PYTHON_VERSION${NC}\n"

# 2. Crear virtualenv si no existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creando virtualenv...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtualenv creado${NC}\n"
else
    echo -e "${GREEN}✅ Virtualenv ya existe${NC}\n"
fi

# 3. Activar virtualenv
echo -e "${YELLOW}🔌 Activando virtualenv...${NC}"
source venv/bin/activate
echo -e "${GREEN}✅ Virtualenv activado${NC}\n"

# 4. Actualizar pip
echo -e "${YELLOW}📦 Actualizando pip...${NC}"
pip install --upgrade pip > /dev/null
echo -e "${GREEN}✅ pip actualizado${NC}\n"

# 5. Instalar dependencias
echo -e "${YELLOW}📚 Instalando dependencias...${NC}"
echo "   (Esto puede tomar unos minutos)"
pip install -r requirements.txt
echo -e "${GREEN}✅ Dependencias instaladas${NC}\n"

# 6. Configurar .env si no existe
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚙️  Creando archivo .env...${NC}"
    cat > .env << 'EOF'
# Django
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))' 2>/dev/null || echo 'change-me-to-a-secure-random-key')

# Database (PostgreSQL local)
# DATABASE_URL=postgresql://user:password@localhost:5432/agrotech_dev

# APIs (obtener de administrador)
EOSDA_API_KEY=
CESIUM_ACCESS_TOKEN=

# Email (opcional para dev)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Cache (opcional)
# REDIS_URL=redis://localhost:6379/0
EOF
    echo -e "${GREEN}✅ Archivo .env creado${NC}"
    echo -e "${YELLOW}⚠️  Edita .env y agrega tus API keys${NC}\n"
else
    echo -e "${GREEN}✅ Archivo .env ya existe${NC}\n"
fi

# 7. Crear directorios necesarios
echo -e "${YELLOW}📁 Creando directorios...${NC}"
mkdir -p logs backups media staticfiles
echo -e "${GREEN}✅ Directorios creados${NC}\n"

# 8. Migraciones
echo -e "${YELLOW}🗄️  Aplicando migraciones...${NC}"
if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}⚠️  DATABASE_URL no configurada, usando SQLite${NC}"
    python manage.py migrate --noinput
else
    python manage.py migrate_schemas --shared --noinput
fi
echo -e "${GREEN}✅ Migraciones aplicadas${NC}\n"

# 9. Crear superusuario (opcional)
echo -e "${YELLOW}👤 ¿Crear superusuario? (s/n)${NC}"
read -r CREATE_SUPER
if [ "$CREATE_SUPER" = "s" ] || [ "$CREATE_SUPER" = "S" ]; then
    python manage.py createsuperuser
fi

# 10. Collectstatic
echo -e "\n${YELLOW}📦 Recolectando archivos estáticos...${NC}"
python manage.py collectstatic --noinput > /dev/null
echo -e "${GREEN}✅ Estáticos recolectados${NC}\n"

# 11. Ejecutar tests
echo -e "${YELLOW}🧪 ¿Ejecutar tests? (s/n)${NC}"
read -r RUN_TESTS
if [ "$RUN_TESTS" = "s" ] || [ "$RUN_TESTS" = "S" ]; then
    bash scripts/run_tests.sh --quick
fi

# 12. Resumen
echo -e "\n${GREEN}"
echo "╔═══════════════════════════════════════════════╗"
echo "║           ✅ Setup Completado!                ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "${BLUE}Próximos pasos:${NC}"
echo ""
echo "1. Editar .env con tus API keys"
echo "   - EOSDA_API_KEY"
echo "   - CESIUM_ACCESS_TOKEN"
echo ""
echo "2. Activar virtualenv:"
echo "   ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo "3. Iniciar servidor:"
echo "   ${YELLOW}python manage.py runserver${NC}"
echo ""
echo "4. Acceder a:"
echo "   - App: ${BLUE}http://localhost:8000${NC}"
echo "   - Admin: ${BLUE}http://localhost:8000/admin${NC}"
echo "   - API Docs: ${BLUE}http://localhost:8000/api/docs${NC}"
echo ""
echo "5. Ejecutar tests:"
echo "   ${YELLOW}bash scripts/run_tests.sh --coverage${NC}"
echo ""
echo -e "${GREEN}¡Listo para desarrollar! 🚀${NC}\n"
