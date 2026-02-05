"""
Configuración de logging estructurado para AgroTech Digital.
"""
import logging
import sys
from pathlib import Path

# Colores para console logging
class ColoredFormatter(logging.Formatter):
    """Formatter con colores para consola."""
    
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',   # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def get_logger(name):
    """
    Obtiene un logger configurado para un módulo específico.
    
    Args:
        name: Nombre del módulo (usualmente __name__)
        
    Returns:
        logging.Logger: Logger configurado
    """
    return logging.getLogger(name)


def configure_logging(settings_module='production'):
    """
    Configura logging para toda la aplicación.
    
    Args:
        settings_module: 'production', 'local', o 'base'
    """
    from django.conf import settings
    
    # Nivel por defecto
    level = 'WARNING' if settings_module == 'production' else 'DEBUG'
    
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '[{levelname}] {asctime} {name} {module}:{lineno} - {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'simple': {
                'format': '[{levelname}] {name} - {message}',
                'style': '{',
            },
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
            },
        },
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse',
            },
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
                'stream': sys.stdout,
            },
            'file_errors': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': Path(settings.BASE_DIR) / 'logs' / 'errors.log',
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 5,
                'formatter': 'verbose',
            },
            'file_eosda': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': Path(settings.BASE_DIR) / 'logs' / 'eosda.log',
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 3,
                'formatter': 'verbose',
            },
            'null': {
                'class': 'logging.NullHandler',
            },
        },
        'root': {
            'level': level,
            'handlers': ['console'],
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'django.security': {
                'handlers': ['console', 'file_errors'],
                'level': 'INFO',
                'propagate': False,
            },
            'parcels': {
                'handlers': ['console', 'file_eosda'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'parcels.eosda': {
                'handlers': ['console', 'file_eosda'],
                'level': 'INFO',
                'propagate': False,
            },
            'authentication': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'crop': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'inventario': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'labores': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'RRHH': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    
    return LOGGING
