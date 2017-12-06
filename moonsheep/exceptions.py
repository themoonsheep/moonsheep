class PresenterNotDefined(Exception):
    pass


class TaskWithNoTemplateNorForm(Exception):
    def __init__(self, klass):
        self.klass = klass

    def __str__(self):
        return "Task {} does not define task_form_template nor task_form.".format(self.klass)


class TaskSourceNotDefined(Exception):
    pass


class NoTasksLeft(Exception):
    pass

