class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class TaskRegistry:
    def __init__(self):
        self.registry = []  # model_class

    def register(self, model):
        if model in self.registry:
            raise AlreadyRegistered('The model {0} is already registered in stats registry'.format(model.__name__))
        self.registry.append(model.__module__ + '.' + model.__name__)
        return model

    def unregister(self, model):
        if model not in self.registry:
            raise NotRegistered('The model {0} is not registered'.format(model.__name__))
        self.registry.remove(model.__module__ + '.' + model.__name__)

    def is_registered(self, model):
        return model in self.registry

    def clear(self):
        self.registry.clear()


initial_task = TaskRegistry()
base_task = TaskRegistry()
