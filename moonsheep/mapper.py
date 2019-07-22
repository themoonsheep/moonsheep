import importlib
import inspect
import json
from typing import Callable

from django.core import serializers
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


def klass_from_name(name):
    parts = name.split('.')
    module_name, class_name = '.'.join(parts[:-1]), parts[-1]
    try:
        module_path = importlib.import_module(module_name)
        klass = getattr(module_path, class_name)
    except (ImportError, AttributeError) as e:
        raise Exception("Couldn't import class {}".format(name)) from e
    return klass


# TODO unused
def export_model(format_name, model_name):
    model = klass_from_name(model_name)
    data = json.loads(serializers.serialize(format_name, model.objects.all()))
    model_data = [obj['fields'] for obj in data]
    return model_data
