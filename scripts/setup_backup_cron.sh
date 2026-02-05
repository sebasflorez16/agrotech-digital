#!/bin/bash

# Script para configurar cron job de backup automático
# Ejecutar con: bash scripts/setup_backup_cron.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔧 Configurando backup automático para AgroTech Digital"
echo "📁 Directorio del proyecto: $PROJECT_DIR"

# Crear directorio de backups
mkdir -p "$PROJECT_DIR/backups"
echo "✅ Directorio de backups creado: $PROJECT_DIR/backups"

# Hacer el script ejecutable
chmod +x "$SCRIPT_DIR/backup_database.py"
echo "✅ Script de backup hecho ejecutable"

# Crear wrapper script para cron
cat > "$SCRIPT_DIR/backup_cron_wrapper.sh" << EOF
#!/bin/bash
# Wrapper para ejecutar backup desde cron

# Cargar variables de entorno
export \$(cat $PROJECT_DIR/.env | xargs)

# Activar virtualenv si existe
if [ -d "$PROJECT_DIR/venv" ]; then
    source $PROJECT_DIR/venv/bin/activate
fi

# Ejecutar backup
cd $PROJECT_DIR
python $SCRIPT_DIR/backup_database.py --output-dir $PROJECT_DIR/backups --keep-last 7

# Log resultado
echo "\$(date): Backup ejecutado" >> $PROJECT_DIR/logs/backup.log
EOF

chmod +x "$SCRIPT_DIR/backup_cron_wrapper.sh"
echo "✅ Wrapper de cron creado"

# Sugerir línea de cron
echo ""
echo "📋 Para agregar backup automático diario a las 2 AM, ejecuta:"
echo ""
echo "crontab -e"
echo ""
echo "Y agrega esta línea:"
echo ""
echo "0 2 * * * $SCRIPT_DIR/backup_cron_wrapper.sh"
echo ""
echo "O para backup cada 6 horas:"
echo "0 */6 * * * $SCRIPT_DIR/backup_cron_wrapper.sh"
echo ""
echo "✅ Setup completado!"
