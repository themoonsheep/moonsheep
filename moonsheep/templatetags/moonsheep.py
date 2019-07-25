from django.template import Library

from moonsheep.tasks import AbstractTask

register = Library()


@register.inclusion_tag('token.html')
def moonsheep_token(task: AbstractTask):
    return {
        'task_id': task.instance.id,
        'task_type': task.name
    }
