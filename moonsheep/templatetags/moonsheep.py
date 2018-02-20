from django.template import Library

register = Library()


@register.inclusion_tag('token.html')
def moonsheep_token(task):
    return {
        'moonsheep_task_id': task.id,
        'moonsheep_project_id': task.project_id,
        'moonsheep_url': task.url,
    }


@register.filter
def key(dictionary, key):
    return dictionary.get(key) if dictionary else None
