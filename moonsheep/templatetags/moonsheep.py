from django.template import Library

register = Library()


@register.inclusion_tag('token.html')
def moonsheep_token(task):
    return {
        'task_id': task.id,
        'project_id': task.project_id
    }
