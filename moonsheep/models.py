from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User, AbstractUser
from django.db import models
from django.utils.translation import ugettext as _
from django.core import validators
import json
from django.core.serializers.json import DjangoJSONEncoder


class JSONField(models.TextField):
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

    def to_python(self, value):
        if value == "":
            return None

        try:
            if isinstance(value, str):
                # TODO test datetime saving `object_hook`
                return json.loads(value, cls=DjangoJSONEncoder)
        except ValueError:
            pass
        return value

    def from_db_value(self, value, *args):
        return self.to_python(value)

    def get_db_prep_save(self, value, *args, **kwargs):
        if value == "":
            return None
        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)
        return value


class Task(models.Model):
    """
    A specific Task that users will work on.

    It is uniquely defined by task class/type and params
    """

    # TODO issue with circular imports; resolve it otherwise, add choices dynamically or drop it # from .registry import TASK_TYPES
    type = models.CharField(verbose_name=_("Type"), max_length=255) #, choices=[(t, t) for t in TASK_TYPES])
    """Full reference (with module) to task class name"""

    params = JSONField(blank=True)
    """Params specifying the task, that will be passed to user"""

    # TODO count priority + interface
    priority = models.DecimalField(decimal_places=2, max_digits=3, default=1.0,
                                   validators=[validators.MaxValueValidator(1.0), validators.MinValueValidator(0.0)], )
    """Priority of the task, set manually or computed by defined functionD from other fields. Scale: 0.0 - 1.0"""

    # States
    OPEN = 'open'
    DIRTY = 'dirty'
    CROSSCHECKED = 'checked'
    CLOSED_MANUALLY = 'manual'

    state = models.CharField(max_length=10, choices=[(s, s) for s in [OPEN, DIRTY, CROSSCHECKED, CLOSED_MANUALLY]],
                             default=OPEN)

    class Meta:
        constraints = [
            # Type and params fully define an unique task
            models.UniqueConstraint(fields=['type', 'params'], name='unique_type_params')
        ]
        indexes = [
            # TODO based on queries, most likely: models.Index(fields=['state', 'priority']),
        ]

    def __str__(self):
        return self.type + self.params


class Entry(models.Model, ModelBackend):
    task = models.ForeignKey(Task, models.CASCADE)
    user = models.ForeignKey(User, models.CASCADE, null=True)  # TODO remove null in #130
    data = JSONField()

    class Meta:
        constraints = [
            # There can be only one user's entry for given task. Django doesn't support compound keys
            models.UniqueConstraint(fields=['task', 'user'], name='unique_task_user')
        ]

# TODO Research how to best organize users
# https://docs.djangoproject.com/en/2.2/topics/auth/customizing/
# Custom user: https://www.fomfus.com/articles/how-to-use-email-as-username-for-django-authentication-removing-the-username
# Custom backend: https://stackoverflow.com/a/37332393/803174

# class User(AbstractUser):
#     pass
