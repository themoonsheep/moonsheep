from moonsheep.settings import * #NOQA

SECRET_KEY = 'fake-key'

INSTALLED_APPS = [
    "moonsheep",
    'django.contrib.auth',
    'django.contrib.contenttypes',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

MOONSHEEP_TASK_SOURCE = ''
MOONSHEEP_BASE_TASKS = ['task1', 'task2']
