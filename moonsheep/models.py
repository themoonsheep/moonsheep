import inspect
from typing import Callable
from django.db import models as dmodels


class ModelMapper:
    def __init__(self, klass, data, **kwargs):
        def default_getter(param_name:str):
            return data[param_name].strip()

        self.klass = klass
        self.fields = {}
        self.getter = default_getter

        allowed_keys = ['getter']
        for k, v in kwargs.items():
            if k not in allowed_keys:
                raise Exception("ModelMapper doesn't allow argument '{}'".format(k))
            self.__setattr__(k, v)

    def map_one(self, fld_name: str, param_name: str=None,
             convert: Callable=lambda x: x, missing: Callable=None):
        if param_name is None:
            param_name = fld_name
        try:
            v = self.getter(param_name)
        except KeyError:
            if missing is not None:
                self.fields[fld_name] = missing()
            return self

        if v is not None and v != '':
            self.fields[fld_name] = convert(v)

        return self

    def map(self, exclude=[], rename: dict={}):
        for f in self.klass._meta.get_fields():
            if f.name in exclude:
                continue

            convert = lambda x: x
            missing = None

            if isinstance(f, dmodels.BooleanField):
                convert = lambda x: bool(x)
                # checkboxes won't be in POST if they are not checked
                # TODO how does it affect processing forms?
                missing = lambda: False

            elif isinstance(f, dmodels.NullBooleanField):
                convert = lambda x: bool(x)

            elif isinstance(f, dmodels.IntegerField):
                convert = lambda x: int(x)

            elif isinstance(f, dmodels.DecimalField):
                convert = lambda x: float(x)

            self.map_one(f.name, rename.get(f.name, f.name), convert=convert, missing=missing)

        return self

    def create(self, **extras):
        params = self.fields
        params.update(extras)
        return self.klass(**params)
