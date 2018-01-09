class PresenterNotDefined(Exception):
    pass


class TaskMustSetTemplate(Exception):
    def __init__(self, klass):
        self.klass = klass

    def __str__(self):
        return "Task {} must define template_name.".format(self.klass)


class TaskSourceNotDefined(Exception):
    pass


class NoTasksLeft(Exception):
    pass

