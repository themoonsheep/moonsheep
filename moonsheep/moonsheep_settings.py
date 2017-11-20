from django.conf import settings

# tasks sources
RANDOM_SOURCE = 'random'
PYBOSSA_SOURCE = 'pybossa'
DEFAULT_SOURCE = RANDOM_SOURCE

TASK_SOURCE = getattr(settings, 'MOONSHEEP_TASK_SOURCE', DEFAULT_SOURCE)

# pybossa endpoints
DEFAULT_PYBOSSA_URL = 'http://localhost:5000'
DEFAULT_PYBOSSA_PROJECT_ID = 1

PYBOSSA_API_BASE_URL = getattr(settings, 'PYBOSSA_URL', DEFAULT_PYBOSSA_URL).rstrip('/') + "/api"
PYBOSSA_PROJECT_ID = getattr(settings, 'PYBOSSA_PROJECT_ID', DEFAULT_PYBOSSA_PROJECT_ID)

# http://docs.pybossa.com/api/crud/
PYBOSSA_PROJECT_URL = PYBOSSA_API_BASE_URL + "/project"
PYBOSSA_TASKS_URL = PYBOSSA_API_BASE_URL + "/task"
PYBOSSA_TASK_RUN_URL = PYBOSSA_API_BASE_URL + "/taskrun"
PYBOSSA_NEW_TASK_URL = PYBOSSA_API_BASE_URL + "/project/" + str(settings.PYBOSSA_PROJECT_ID) + "/newtask"
