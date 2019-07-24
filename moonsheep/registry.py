# encoding: utf-8

from contextlib import contextmanager

# TODO won't dict with actual classes be helpful here?
TASK_TYPES = []


def register(task_class):
    from .tasks import AbstractTask
    if not issubclass(task_class, AbstractTask):
        raise ValueError('Task_class must subclass AbstractTask')

    if task_class not in TASK_TYPES:
        TASK_TYPES.append(task_class.__module__ + '.' + task_class.__name__)

    return task_class


def unregister(task_class):
    if task_class in TASK_TYPES:
        TASK_TYPES.remove(task_class.__module__ + '.' + task_class.__name__)


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


def register_task():
    """
    Decorator to register a given task class

    @register_task()
    class TransactionTask(AbstractTask):

    """
    def _task_wrapper(task_class):
        if not task_class:
            raise ValueError('Task Class must be passed to register.')

        register(task_class)

        return task_class

    return _task_wrapper
