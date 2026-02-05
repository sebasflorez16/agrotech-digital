#!/usr/bin/env python
"""
Script de backup automático de la base de datos PostgreSQL.
Puede ejecutarse manualmente o via cron job.

Uso:
    python scripts/backup_database.py [--output-dir /path/to/backups]
"""
import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def parse_database_url(database_url):
    """
    Parse DATABASE_URL en componentes.
    
    Format: postgresql://user:password@host:port/database
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(database_url)
    
    return {
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/')
    }


def create_backup(db_config, output_dir):
    """
    Crea backup de la base de datos usando pg_dump.
    
    Args:
        db_config: Diccionario con configuración de BD
        output_dir: Directorio donde guardar el backup
    
    Returns:
        Path al archivo de backup creado
    """
    # Crear nombre de archivo con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"agrotech_backup_{timestamp}.sql"
    output_path = output_dir / filename
    
    logger.info(f"Iniciando backup de base de datos: {db_config['database']}")
    logger.info(f"Archivo de salida: {output_path}")
    
    # Configurar variables de entorno para pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']
    
    # Comando pg_dump
    cmd = [
        'pg_dump',
        '-h', db_config['host'],
        '-p', str(db_config['port']),
        '-U', db_config['user'],
        '-d', db_config['database'],
        '-F', 'c',  # Custom format (comprimido)
        '--no-owner',
        '--no-acl',
        '-f', str(output_path)
    ]
    
    try:
        # Ejecutar pg_dump
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"✅ Backup completado exitosamente: {output_path}")
        
        # Verificar tamaño del archivo
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Tamaño del backup: {size_mb:.2f} MB")
        
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error al crear backup: {e}")
        logger.error(f"Stderr: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        raise


def cleanup_old_backups(output_dir, keep_last=7):
    """
    Elimina backups antiguos, manteniendo solo los últimos N.
    
    Args:
        output_dir: Directorio de backups
        keep_last: Número de backups a mantener
    """
    logger.info(f"Limpiando backups antiguos (manteniendo últimos {keep_last})...")
    
    # Listar todos los archivos de backup
    backup_files = sorted(
        output_dir.glob('agrotech_backup_*.sql'),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    # Eliminar los más antiguos
    for backup_file in backup_files[keep_last:]:
        logger.info(f"Eliminando backup antiguo: {backup_file.name}")
        backup_file.unlink()
    
    logger.info(f"Limpieza completada. Backups restantes: {min(len(backup_files), keep_last)}")


def upload_to_s3(backup_path, bucket_name):
    """
    Opcionalmente sube el backup a S3 (requiere boto3).
    
    Args:
        backup_path: Path al archivo de backup
        bucket_name: Nombre del bucket S3
    """
    try:
        import boto3
        
        logger.info(f"Subiendo backup a S3: {bucket_name}")
        
        s3_client = boto3.client('s3')
        s3_key = f"backups/{backup_path.name}"
        
        s3_client.upload_file(
            str(backup_path),
            bucket_name,
            s3_key
        )
        
        logger.info(f"✅ Backup subido a S3: s3://{bucket_name}/{s3_key}")
        
    except ImportError:
        logger.warning("⚠️ boto3 no instalado, saltando upload a S3")
    except Exception as e:
        logger.error(f"❌ Error al subir a S3: {e}")


def main():
    parser = argparse.ArgumentParser(description='Backup de base de datos AgroTech')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'backups',
        help='Directorio de salida para backups'
    )
    parser.add_argument(
        '--keep-last',
        type=int,
        default=7,
        help='Número de backups a mantener (default: 7)'
    )
    parser.add_argument(
        '--s3-bucket',
        type=str,
        help='Nombre del bucket S3 para subir backup (opcional)'
    )
    
    args = parser.parse_args()
    
    # Crear directorio de backups si no existe
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Obtener DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL no está configurada")
        sys.exit(1)
    
    # Parsear configuración de BD
    db_config = parse_database_url(database_url)
    
    try:
        # Crear backup
        backup_path = create_backup(db_config, args.output_dir)
        
        # Upload a S3 si se especificó
        if args.s3_bucket:
            upload_to_s3(backup_path, args.s3_bucket)
        
        # Limpiar backups antiguos
        cleanup_old_backups(args.output_dir, args.keep_last)
        
        logger.info("✅ Proceso de backup completado exitosamente")
        
    except Exception as e:
        logger.error(f"❌ El proceso de backup falló: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
