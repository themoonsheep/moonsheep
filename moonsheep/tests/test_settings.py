SECRET_KEY = 'fake-key'

INSTALLED_APPS = [
    "moonsheep",
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

MOONSHEEP_TASK_SOURCE = ''
MOONSHEEP_DEVELOPMENT_MODE = False
