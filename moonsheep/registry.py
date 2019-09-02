# encoding: utf-8

from contextlib import contextmanager

from moonsheep.mapper import klass_from_name
from moonsheep.tasks import AbstractTask
from .settings import MOONSHEEP
import django.db.models


def register(task_class):
    from .tasks import AbstractTask
    if not issubclass(task_class, AbstractTask):
        raise ValueError('Task_class must subclass AbstractTask')

    if task_class not in TASK_TYPES:
        TASK_TYPES.append(task_class.name)

    return task_class


def unregister(task_class):
    if task_class in TASK_TYPES:
        TASK_TYPES.remove(task_class.name)


@contextmanager
def loaded_tasks(*task_classes):
    """
    Load task(s) for testing purposes
    e.g.
    ```
    from . import registry
    with registry.loaded_tasks(MyTestedTask):
        # run tests with task loaded
    ```
    """

    for t in task_classes:
        register(t)
    try:
        yield
    finally:
        for t in task_classes:
            unregister(t)


def document(on_import_create=[]):
    """
    Decorator to register model which saves documents

    ```
    @document(on_import_create=['app.tasks.FindTableTask'])
    class Report(models.Model):
    ```
    """

    def _task_wrapper(model_class):
        # TODO check: model_class should have url parameter

        if not len(on_import_create):
            raise ValueError(
                "You should specify tasks to create on document upload using on_import_create decorator parameter")

        MOONSHEEP['DOCUMENT_MODEL'] = model_class
        MOONSHEEP['DOCUMENT_INITIAL_TASKS'] = on_import_create

        return model_class

    return _task_wrapper


def get_document_model():
    if 'DOCUMENT_MODEL' not in MOONSHEEP:
        raise ValueError("Project must define a default document model using @document annotation on a class")
    if not issubclass(MOONSHEEP['DOCUMENT_MODEL'], django.db.models.Model):
        raise ValueError("Document model should implement Django's Model")

    return MOONSHEEP['DOCUMENT_MODEL']


# TODO won't dict with actual classes be helpful here?
# TODO move it into settings to avoid circular dependencies?
TASK_TYPES = []
