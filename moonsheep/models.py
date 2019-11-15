import random

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core import validators
from django.db import models
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from moonsheep.json_field import JSONField


def generate_password(bits=160):
    return "%x" % random.getrandbits(bits)


class UserManager(BaseUserManager):
    """
    Define a model manager for User model with no username field.

    Copied and modified from django.contrib.auth.models.UserManager
    Kudos to https://www.fomfus.com/articles/how-to-use-email-as-username-for-django-authentication-removing-the-username
    for pointing it out and giving a nice how-to
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

    def create_pseudonymous(self, nickname):
        if not nickname:
            raise ValueError('Nickname must be given')
        email = self.normalize_email(slugify(nickname) + User.PSEUDONYMOUS_DOMAIN)

        return self._create_user(email, generate_password(), nickname=nickname)


class User(AbstractUser):
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    username = None
    email = models.EmailField(_('email address'), unique=True)

    nickname = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        blank=True,
        error_messages={
            'unique': _("A user with that nickname already exists."),
        },
    )

    # gdpr_consents TODO #139 string: policy codes separated by semicolon

    PSEUDONYMOUS_DOMAIN = "@pseudonymous.moonsheep.org"


class TaskQuerySet(models.QuerySet):
    def dirty(self):
        return self.filter(state=Task.DIRTY).order_by('-priority', '-id')

    def next_dirty(self, task_id) -> 'Task':
        priority = Task.objects.values_list('priority', flat=True).get(pk=task_id)
        task = Task.objects.raw(
            "SELECT id FROM moonsheep_task WHERE state = 'dirty' AND (priority, id) < (%s, %s) ORDER BY priority DESC, id DESC"
            " FETCH FIRST 1 ROWS ONLY",
            [priority, task_id])

        if len(task):
            return task[0]
        else:
            return None


class Task(models.Model):
    """
    A specific Task that users will work on.

    It is uniquely defined by task class/type and params
    """

    objects = TaskQuerySet.as_manager()

    # TODO issue with circular imports; resolve it otherwise, add choices dynamically or drop it # from .registry import TASK_TYPES
    type = models.CharField(verbose_name=_("Type"), max_length=255)  # , choices=[(t, t) for t in TASK_TYPES])
    """Full reference (with module) to task class name"""

    params = JSONField()
    """Params specifying the task, that will be passed to user"""

    parent = models.ForeignKey('Task', models.CASCADE, null=True, blank=True, related_name="children")
    """Set if this task is a child of another"""

    # TODO can we make it "dynamic"?
    doc_id = models.IntegerField()
    """Pointing to document_id being processed by this task"""

    # TODO count priority + interface https://github.com/themoonsheep/moonsheep/issues/50
    # TODO ! document how to set priority for first task and all dependants
    priority = models.DecimalField(decimal_places=2, max_digits=3, default=0.5,
                                   validators=[validators.MaxValueValidator(1.0), validators.MinValueValidator(0.0)], )
    """Priority of the task, set manually or computed by defined functionD from other fields. Scale: 0.0 - 1.0"""

    own_progress = models.DecimalField(decimal_places=3, max_digits=6, default=0,
                                       validators=[validators.MaxValueValidator(100), validators.MinValueValidator(0)])

    # TODO could add confidence here (maybe packed with all fields confidences)

    total_progress = models.DecimalField(decimal_places=3, max_digits=6, default=0,
                                         validators=[validators.MaxValueValidator(100),
                                                     validators.MinValueValidator(0)])
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
        return f"{self.type}[{self.id}]"


class Entry(models.Model):
    task = models.ForeignKey(Task, models.CASCADE)
    user = models.ForeignKey(User, models.CASCADE)
    data = JSONField()

    class Meta:
        constraints = [
            # There can be only one user's entry for given task. Django doesn't support compound keys
            models.UniqueConstraint(fields=['task', 'user'], name='unique_task_user')
        ]
        verbose_name_plural = "entries"
