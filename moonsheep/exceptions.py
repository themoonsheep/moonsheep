class PresenterNotDefined(Exception):
    pass


class TaskMustSetTemplate(Exception):
    def __init__(self, klass):
        self.cls = klass

    def __str__(self):
        return "Task {} must define template_name.".format(self.cls)


class NoTasksLeft(Exception):
    pass
