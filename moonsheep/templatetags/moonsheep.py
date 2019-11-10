import os
import urllib.parse
from decimal import Decimal

from django.db.models import Count, Sum, IntegerField, Avg
from django.db.models.expressions import RawSQL
from django.template import Library
from django.template.defaultfilters import stringfilter
from django.urls import reverse

from moonsheep.settings import MOONSHEEP

register = Library()


@register.inclusion_tag('token.html')
def moonsheep_token(task: 'AbstractTask'):
    return {
        'task_id': task.instance.id,
        'task_type': task.name
    }


@register.simple_tag
def document_change_url(instance):
    meta = type(instance)._meta
    view_name = 'admin:%s_%s_change' % (meta.app_label, meta.model_name)
    return reverse(view_name, args=(instance.id,))


@register.filter
@stringfilter
def task_name(value):
    return value.split('.').pop()


@register.filter
@stringfilter
def pretty_url(value):
    return urllib.parse.unquote(os.path.basename(value))


@register.simple_tag
def stats_documents_verified():
    """
    Shows stats regarding fully verified documents

    - verified
    - verified_percents
    - total
    """
    # TODO cache it
    docs = MOONSHEEP['DOCUMENT_MODEL'].objects \
        .annotate(verified=RawSQL("CASE WHEN progress == 100 THEN 1 ELSE 0 END", ())) \
        .aggregate(
        verified=Sum("verified", output_field=IntegerField()),
        total=Count('id'),
        total_progress=Avg('progress')
    )
    docs['verified_percents'] = Decimal(docs['verified']) / docs['total']
    docs['remaining'] = int(docs['total'] - docs['verified'])

    return docs
