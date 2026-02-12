#!/bin/bash
# ============================================
# AgroTech Digital - Arranque Local Completo
# ============================================
# Simula producción: Backend (Django :8000) + Frontend (Netlify :8080)
# 
# USO:
#   ./scripts/start-local.sh          → Arranca backend + frontend
#   ./scripts/start-local.sh backend  → Solo backend
#   ./scripts/start-local.sh frontend → Solo frontend
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$(dirname "$BACKEND_DIR")/agrotech-client-frontend"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  🚀 AgroTech Digital - Entorno Local${NC}"
echo -e "${BLUE}============================================${NC}"

# Verificar PostgreSQL
echo -e "\n${YELLOW}1. Verificando PostgreSQL...${NC}"
if pg_isready -q 2>/dev/null; then
    echo -e "   ${GREEN}✅ PostgreSQL corriendo${NC}"
else
    echo -e "   ${RED}❌ PostgreSQL no está corriendo${NC}"
    echo -e "   ${YELLOW}   Intentando arrancar...${NC}"
    brew services start postgresql@14 2>/dev/null || sudo -u postgres /Library/PostgreSQL/17/bin/pg_ctl start -D /Library/PostgreSQL/17/data 2>/dev/null
    sleep 2
    if pg_isready -q 2>/dev/null; then
        echo -e "   ${GREEN}✅ PostgreSQL arrancado${NC}"
    else
        echo -e "   ${RED}❌ No se pudo arrancar PostgreSQL. Verifica la instalación.${NC}"
        exit 1
    fi
fi

# Verificar base de datos
echo -e "\n${YELLOW}2. Verificando base de datos...${NC}"
if psql -U postgres -h localhost -d agrotech -c "SELECT 1;" &>/dev/null; then
    echo -e "   ${GREEN}✅ Base de datos 'agrotech' disponible${NC}"
else
    echo -e "   ${RED}❌ No se puede conectar a la BD 'agrotech'${NC}"
    exit 1
fi

# Verificar migraciones
echo -e "\n${YELLOW}3. Verificando migraciones...${NC}"
cd "$BACKEND_DIR"
PENDING=$(python manage.py showmigrations --settings=config.settings.local 2>/dev/null | grep "\[ \]" | wc -l)
if [ "$PENDING" -gt 0 ]; then
    echo -e "   ${YELLOW}⚠️ $PENDING migraciones pendientes. Ejecutando...${NC}"
    python manage.py migrate_schemas --settings=config.settings.local 2>&1 | tail -5
else
    echo -e "   ${GREEN}✅ Migraciones al día${NC}"
fi

# Verificar tenants
echo -e "\n${YELLOW}4. Verificando tenants...${NC}"
python manage.py shell --settings=config.settings.local -c "
from django_tenants.utils import get_tenant_model, get_tenant_domain_model
T = get_tenant_model()
D = get_tenant_domain_model()
for t in T.objects.all():
    domains = ', '.join([d.domain for d in D.objects.filter(tenant=t)])
    print(f'   ✅ {t.schema_name} → {domains}')
" 2>&1 | grep -v "GDAL"

start_backend() {
    echo -e "\n${YELLOW}5. Arrancando Backend (Django :8000)...${NC}"
    cd "$BACKEND_DIR"
    
    # Matar proceso anterior si existe
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    
    DJANGO_SETTINGS_MODULE=config.settings.local python manage.py runserver 8000 &
    BACKEND_PID=$!
    sleep 2
    
    if curl -s http://localhost:8000/health/ | grep -q "ok"; then
        echo -e "   ${GREEN}✅ Backend corriendo en http://localhost:8000${NC}"
    else
        echo -e "   ${RED}❌ Backend no respondió${NC}"
    fi
}

start_frontend() {
    echo -e "\n${YELLOW}6. Arrancando Frontend (Netlify Dev :8080)...${NC}"
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        echo -e "   ${RED}❌ Frontend no encontrado en: $FRONTEND_DIR${NC}"
        return 1
    fi
    
    cd "$FRONTEND_DIR"
    
    # Matar proceso anterior si existe
    lsof -ti:8080 | xargs kill -9 2>/dev/null
    
    # Cambiar a configuración local
    bash scripts/switch-env.sh local
    
    # Verificar si netlify-cli está instalado
    if ! command -v netlify &>/dev/null; then
        echo -e "   ${YELLOW}Instalando Netlify CLI...${NC}"
        npm install -g netlify-cli
    fi
    
    netlify dev --port 8080 &
    FRONTEND_PID=$!
    sleep 3
    
    echo -e "   ${GREEN}✅ Frontend corriendo en http://localhost:8080${NC}"
}

# Mostrar URLs de acceso
show_urls() {
    echo -e "\n${BLUE}============================================${NC}"
    echo -e "${GREEN}  🌐 URLs de Acceso Local${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo -e "  ${YELLOW}Landing/Billing (public):${NC}"
    echo -e "    http://localhost:8080"
    echo -e ""
    echo -e "  ${YELLOW}Dashboard tenant 'prueba':${NC}"
    echo -e "    http://prueba.localhost:8080"
    echo -e ""
    echo -e "  ${YELLOW}Backend API directa:${NC}"
    echo -e "    http://prueba.localhost:8000/api/parcels/parcel/"
    echo -e ""
    echo -e "  ${YELLOW}Login:${NC}"
    echo -e "    http://prueba.localhost:8080/login"
    echo -e ""
    echo -e "  ${YELLOW}Credenciales de prueba:${NC}"
    echo -e "    Usuario: admin | Email: admin@gmail.com"
    echo -e "${BLUE}============================================${NC}"
    echo -e ""
    echo -e "  ${RED}Ctrl+C para detener todo${NC}"
}

# Cleanup al salir
cleanup() {
    echo -e "\n${YELLOW}Deteniendo servicios...${NC}"
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    
    # Restaurar netlify.toml de producción
    cd "$FRONTEND_DIR" 2>/dev/null && bash scripts/switch-env.sh prod 2>/dev/null
    
    echo -e "${GREEN}✅ Entorno local detenido${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Ejecutar según argumento
case "${1:-all}" in
    backend)
        start_backend
        show_urls
        wait $BACKEND_PID
        ;;
    frontend)
        start_frontend
        show_urls
        wait $FRONTEND_PID
        ;;
    all|*)
        start_backend
        start_frontend
        show_urls
        wait
        ;;
esac
