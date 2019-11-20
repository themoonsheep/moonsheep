# TODO A tested solution for importing & overriding settings:
#  https://github.com/encode/django-rest-framework/blob/master/rest_framework/settings.py
# We go with more basic solution
# 1) isting here default settings
# 2) importing them in a project: from moonsheep.settings import *  # NOQA
# 3) updating them if needed: MOONSHEEP.update({})

# TODO check all these settings on load
MOONSHEEP = {
    'DEV_ROTATE_TASKS': False,
    'MIN_ENTRIES_TO_CROSSCHECK': 3,
    'MIN_ENTRIES_TO_MARK_DIRTY': 4,
    'FAKER_LOCALE': 'it_IT',  # See supported locales at https://github.com/joke2k/faker#localization
    'USER_AUTHENTICATION': 'nickname'  # available settings: 'nickname', 'anonymous', TODO email #60
    # 'APP': 'myapp'  # needs to be set in project
}

AUTH_USER_MODEL = 'moonsheep.User'

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
