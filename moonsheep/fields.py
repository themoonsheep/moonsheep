from django.core import exceptions
from django.db import models
from django.utils.encoding import force_text, python_2_unicode_compatible


class DateField(models.CharField):
    description = ""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 100
        super(DateField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        return value
        # if isinstance(value, GeoPt):
        #     return value
        # return GeoPt(value)

    def get_prep_value(self, value):
        """prepare the value for database query"""
        if value is None:
            return None
        return force_text(self.to_python(value))

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

