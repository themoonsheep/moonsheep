import json
from json import JSONDecodeError

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.contrib.postgres.fields import JSONField as PostgresJSONField


class JSONField(PostgresJSONField):
    def __init__(self, encoder=DjangoJSONEncoder, **options):
        super().__init__(encoder=encoder, **options)

    def from_db_value(self, value, expression, connection):
        if isinstance(value, str):
            # TODO test datetime saving `object_hook`
            # TODO most likely we would have to add some guessing for the types encoded by DjangoJSONEncoder
            try:
                return json.loads(value)
            except JSONDecodeError as e:
                # TODO this should be handled by validation
                e.msg += ': ' + value[max(0, e.pos - 10):e.pos] + '>here>' + value[e.pos:min(e.pos + 10, len(value))]

        return value


# TODO delete when squashing migrations
class JSONTextField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.
    Django snippet #1478, Credit: https://stackoverflow.com/a/41839021/803174

    example:
        class Page(models.Model):
            data = JSONField(blank=True, null=True)


        page = Page.objects.get(pk=5)
        page.data = {'title': 'test', 'type': 3}
        page.save()
    """

    # TODO in Django Admin the value is shown as serialized dict with single quotes, it should have been json
    def to_python(self, value):
        if value == "":
            return None

        if isinstance(value, str):
            # TODO test datetime saving `object_hook`
            # TODO most likely we would have to add some guessing for the types encoded by DjangoJSONEncoder
            try:
                return json.loads(value)
            except JSONDecodeError as e:
                # TODO this should be handled by validation
                e.msg += ': ' + value[max(0, e.pos - 10):e.pos] + '>here>' + value[e.pos:min(e.pos + 10, len(value))]

        return value

    def to_json(self, value):
        if value == "":
            return None
        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)
        return value

    def from_db_value(self, value, *args):
        return self.to_python(value)

    def value_to_string(self, obj):
        # Used by seralization framework: manage.py dumpdata
        value = self.value_from_object(obj)

        return str(self.to_json(value))

    def get_prep_value(self, value):
        # Use by lookups (equals to, etc.)
        value = super().get_prep_value(value)

        if isinstance(value, dict):
            return self.to_json(value)

        return self.to_python(value)

    # def get_db_prep_save(self, value, *args, **kwargs):
    #     return self.to_json(value)
