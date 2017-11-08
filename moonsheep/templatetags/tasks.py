from django.template import Library

register = Library()


@register.inclusion_tag('task.html')
def task():
    return {}
