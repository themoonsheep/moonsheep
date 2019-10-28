from django.template import Library
from django.template.defaultfilters import stringfilter
from django.urls import reverse
import django.db.models

from moonsheep.tasks import AbstractTask
from moonsheep.settings import MOONSHEEP

register = Library()


@register.inclusion_tag('token.html')
def moonsheep_token(task: AbstractTask):
    return {
        'task_id': task.instance.id,
        'task_type': task.name
    }


@register.simple_tag
def document_change_url(instance):
    meta = type(instance)._meta
    view_name = 'admin:%s_%s_change' % (meta.app_label, meta.model_name)
    return reverse(view_name, args=(instance.id,))


@register.simple_tag
def progress_of(document_or_task):
    if isinstance(document_or_task, django.db.models.Model):
        doc = document_or_task
        tasks = MOONSHEEP['DOCUMENT_INITIAL_TASKS']
        # TODO #13
    else:
        task = document_or_task
        # TODO

    # TODO #13
    return 81


@register.filter
@stringfilter
def task_name(value):
    return value.split('.').pop()
