class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class Registrable:
    def __init__(self):
        self.registry = []  # model_class

    def register(self, model):
        if model in self.registry:
            raise AlreadyRegistered('The model {0} is already registered in stats registry'.format(model.__name__))
        self.registry.append(model)
        return model

    def unregister(self, model):
        if model not in self.registry:
            raise NotRegistered('The model {0} is not registered'.format(model.__name__))
        self.registry.remove(model)

    def is_registered(self, model):
        return model in self.registry

    def clear(self):
        self.registry.clear()


initial_task = Registrable()
base_task = Registrable()
