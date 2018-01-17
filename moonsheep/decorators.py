def register():
    def _task_wrapper(task):
        if not task:
            raise ValueError('At least one model must be passed to register.')

        from .register import base_task
        base_task.register(task)
        return task
    return _task_wrapper
