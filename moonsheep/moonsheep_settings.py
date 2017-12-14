import pbclient

from django.conf import settings


# tasks sources
RANDOM_SOURCE = 'random'
PYBOSSA_SOURCE = 'pybossa'
DEFAULT_SOURCE = RANDOM_SOURCE

TASK_SOURCE = getattr(settings, 'MOONSHEEP_TASK_SOURCE', DEFAULT_SOURCE)

"""
If set Moonsheep won't communicate with PyBossa and will:
1. serve random mocked tasks
2. send form submissions straight to the verification  
"""
DEVELOPMENT_MODE = getattr(settings, 'MOONSHEEP_DEVELOPMENT_MODE', False)

# pybossa endpoints
DEFAULT_PYBOSSA_URL = 'http://localhost:5000'
DEFAULT_PYBOSSA_PROJECT_ID = 1

PYBOSSA_BASE_URL = getattr(settings, 'PYBOSSA_URL', DEFAULT_PYBOSSA_URL).rstrip('/')
PYBOSSA_API_BASE_URL = PYBOSSA_BASE_URL + "/api"
PYBOSSA_API_KEY = getattr(settings, 'PYBOSSA_API_KEY', '')
PYBOSSA_PROJECT_ID = getattr(settings, 'PYBOSSA_PROJECT_ID', DEFAULT_PYBOSSA_PROJECT_ID)

pbclient.set('endpoint', PYBOSSA_BASE_URL)
pbclient.set('api_key', PYBOSSA_API_KEY)
