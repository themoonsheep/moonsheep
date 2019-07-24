# TODO move away from pybossa, delete this fully

MOONSHEEP = {
    'DEV_ROTATE_TASKS': False
}

TASK_SOURCE = 'random'
RANDOM_SOURCE = 'random'
PYBOSSA_SOURCE = 'pybossa'

# import pbclient
#
# from django.conf import settings
# # tasks sources
# RANDOM_SOURCE = 'random'
# PYBOSSA_SOURCE = 'pybossa'
# DEFAULT_SOURCE = RANDOM_SOURCE
#
# TASK_SOURCE = getattr(settings, 'MOONSHEEP_TASK_SOURCE', DEFAULT_SOURCE)
#
# """
# If set Moonsheep won't communicate with PyBossa and will:
# 1. serve random mocked tasks
# 2. send form submissions straight to the verification
#    won't test cross-checking as there is going to be only one entry, but will allow to test the whole flow
# """
#
# # pybossa endpoints
PYBOSSA_BASE_URL = DEFAULT_PYBOSSA_URL = 'http://localhost:5000'
PYBOSSA_PROJECT_ID = DEFAULT_PYBOSSA_PROJECT_ID = 1

#
# PYBOSSA_BASE_URL = getattr(settings, 'PYBOSSA_URL', DEFAULT_PYBOSSA_URL).rstrip('/')
# PYBOSSA_API_BASE_URL = PYBOSSA_BASE_URL + "/api"
# PYBOSSA_API_KEY = getattr(settings, 'PYBOSSA_API_KEY', '')
# PYBOSSA_PROJECT_ID = getattr(settings, 'PYBOSSA_PROJECT_ID', DEFAULT_PYBOSSA_PROJECT_ID)
#
# pbclient.set('endpoint', PYBOSSA_BASE_URL)
# pbclient.set('api_key', PYBOSSA_API_KEY)

## TODO END of Pybossa settings

REST_FRAMEWORK = {
    'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'rest_framework_json_api.exceptions.exception_handler',
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework_json_api.pagination.JsonApiPageNumberPagination',
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework_json_api.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser'
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework_json_api.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_METADATA_CLASS': 'rest_framework_json_api.metadata.JSONAPIMetadata',
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_json_api.filters.QueryParameterValidationFilter',
        'rest_framework_json_api.filters.OrderingFilter',
        'rest_framework_json_api.django_filters.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
    ),
    'SEARCH_PARAM': 'filter[search]',
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework_json_api.renderers.JSONRenderer',
    ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'vnd.api+json'
}
