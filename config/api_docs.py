"""
Configuración de documentación API con drf-spectacular.
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema


class CustomAutoSchema(AutoSchema):
    """
    Schema personalizado para mejorar la documentación automática.
    """
    
    def get_operation_id(self):
        """Genera IDs de operación más descriptivos."""
        operation_id = super().get_operation_id()
        # Personalizar según necesidades
        return operation_id


SPECTACULAR_SETTINGS = {
    'TITLE': 'AgroTech Digital API',
    'DESCRIPTION': '''
    API REST para el sistema de gestión agrícola AgroTech Digital.
    
    ## Características principales
    
    - **Multi-tenant**: Arquitectura multi-inquilino con schemas separados
    - **Autenticación JWT**: Tokens de acceso y refresh seguros
    - **Análisis Satelital**: Integración completa con EOSDA API
    - **Gestión de Cultivos**: CRUD completo de parcelas, cultivos y labores
    - **Inventario**: Sistema de gestión de insumos y almacenes
    - **RRHH**: Gestión de empleados y recursos humanos
    
    ## Autenticación
    
    Para usar la API, primero obtén un token JWT:
    
    1. POST /api/auth/login/ con username y password
    2. Usa el token `access` en el header: `Authorization: Bearer <token>`
    3. Renueva el token con /api/auth/token/refresh/ cuando expire
    
    ## Rate Limiting
    
    - EOSDA API: Limitado por plan de EOSDA
    - Cache inteligente: 90% de reducción de requests
    - Polling automático: Optimizado para evitar límites
    
    ## Soporte
    
    - Documentación: https://agrotechcolombia.com/docs
    - Email: soporte@agrotechcolombia.com
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'AgroTech Digital Support',
        'email': 'soporte@agrotechcolombia.com',
        'url': 'https://agrotechcolombia.com'
    },
    'LICENSE': {
        'name': 'Proprietary',
    },
    'TAGS': [
        {
            'name': 'Authentication',
            'description': 'Autenticación y gestión de tokens JWT'
        },
        {
            'name': 'Parcels',
            'description': 'Gestión de parcelas/campos agrícolas'
        },
        {
            'name': 'EOSDA',
            'description': 'Análisis satelital con Earth Observing System Data Analytics'
        },
        {
            'name': 'Crops',
            'description': 'Gestión de cultivos y fenología'
        },
        {
            'name': 'Inventory',
            'description': 'Gestión de inventario de insumos'
        },
        {
            'name': 'Labor',
            'description': 'Gestión de labores agrícolas'
        },
        {
            'name': 'RRHH',
            'description': 'Recursos humanos y empleados'
        },
        {
            'name': 'Metrics',
            'description': 'Métricas y monitoreo del sistema'
        },
        {
            'name': 'Health',
            'description': 'Health checks y estado del sistema'
        },
    ],
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/',
    'SCHEMA_PATH_PREFIX_TRIM': True,
    'SERVERS': [
        {
            'url': 'https://agrotechcolombia.com',
            'description': 'Producción (Netlify + Railway)'
        },
        {
            'url': 'https://site-production-208b.up.railway.app',
            'description': 'Backend Railway'
        },
        {
            'url': 'http://localhost:8000',
            'description': 'Desarrollo Local'
        },
    ],
    'SECURITY': [
        {
            'BearerAuth': []
        }
    ],
    'AUTHENTICATION_WHITELIST': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'Token JWT obtenido del endpoint /api/auth/login/'
            }
        }
    },
    'PREPROCESSING_HOOKS': [
        'config.api_docs.custom_preprocessing_hook',
    ],
    'POSTPROCESSING_HOOKS': [
        'config.api_docs.custom_postprocessing_hook',
    ],
    'ENUM_NAME_OVERRIDES': {
        'SoilTypeEnum': 'parcels.models.Parcel.soil_type',
        'TopographyEnum': 'parcels.models.Parcel.topography',
        'UserRoleEnum': 'metrica.users.models.User.role',
    },
    'SORT_OPERATIONS': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'tryItOutEnabled': True,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
    },
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'expandResponses': '200,201',
        'pathInMiddlePanel': True,
    },
}


def custom_preprocessing_hook(endpoints):
    """
    Hook de preprocesamiento para personalizar endpoints.
    """
    # Filtrar endpoints internos
    filtered = []
    for path, path_regex, method, callback in endpoints:
        # Excluir admin y endpoints internos
        if not path.startswith('/admin/'):
            filtered.append((path, path_regex, method, callback))
    return filtered


def custom_postprocessing_hook(result, generator, request, public):
    """
    Hook de postprocesamiento para personalizar el schema final.
    """
    # Agregar información adicional al schema
    result['info']['x-logo'] = {
        'url': 'https://agrotechcolombia.netlify.app/static/img/logo.png',
        'altText': 'AgroTech Digital Logo'
    }
    
    # Agregar ejemplos globales
    if 'components' not in result:
        result['components'] = {}
    
    if 'examples' not in result['components']:
        result['components']['examples'] = {}
    
    result['components']['examples']['ParcelExample'] = {
        'value': {
            'name': 'Finca El Cafetal',
            'description': 'Parcela principal de café',
            'soil_type': 'arcilloso',
            'topography': 'plano',
            'geom': {
                'type': 'Polygon',
                'coordinates': [[
                    [-74.0, 4.0],
                    [-74.01, 4.0],
                    [-74.01, 4.01],
                    [-74.0, 4.01],
                    [-74.0, 4.0]
                ]]
            }
        }
    }
    
    result['components']['examples']['LoginRequest'] = {
        'value': {
            'username': 'usuario@example.com',
            'password': 'password123'
        }
    }
    
    result['components']['examples']['LoginResponse'] = {
        'value': {
            'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
            'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
            'user': {
                'id': 1,
                'username': 'usuario@example.com',
                'email': 'usuario@example.com',
                'name': 'Usuario',
                'role': 'manager'
            }
        }
    }
    
    return result
