import re

from django import forms
from django.core.validators import RegexValidator, ValidationError
from django.template.loader import render_to_string
from django.forms.fields import EMPTY_VALUES
from django.utils.translation import ugettext as _


class MultipleRangeField(forms.CharField):
    default_validators = [RegexValidator(regex="[\w\d]+(-[\w\d]+)?(,[\w\d]+(-[\w\d]+)?)*")]

    def to_python(self, value):
        values = []

        # test if spaces don't
        no_spaces = value.split(" ")
        while "" in no_spaces:
            no_spaces.remove("")
        for idx, val in enumerate(no_spaces):
            if len(no_spaces) > idx + 1 and re.match("^\d+$", val) and re.match("^\d+$", no_spaces[idx+1]):
                raise ValidationError("")
        value = value.replace(" ", "")
        sections = value.split(",")
        for section in sections:
            section_range = section.split("-")
            if len(section_range) > 2:
                raise ValidationError("Wrong range format")
            elif len(section_range) == 2:
                # TODO: include postfixes and prefixes
                v_start = int(section_range[0])
                v_end = int(section_range[1])
                if v_start > v_end:
                    raise ValidationError("Reverse range")
                for v in range(v_start, v_end + 1):
                    if str(v) not in values:
                        values.append(str(v))
            elif len(section_range) == 1:
                if section_range[0] not in values:
                    values.append(section_range[0])
            else:
                raise ValidationError
        return values


class RangeWidget(forms.MultiWidget):
    def __init__(self, widget, *args, **kwargs):
        widgets = (widget, widget)

        super(RangeWidget, self).__init__(widgets=widgets, *args, **kwargs)

    def decompress(self, value):
        return value

    def format_output(self, rendered_widgets):
        widget_context = {'min': rendered_widgets[0], 'max': rendered_widgets[1]}
        return render_to_string('widgets/range_widget.html', widget_context)


class RangeField(forms.MultiValueField):
    default_error_messages = {
        'invalid_start': _(u'Enter a valid start value.'),
        'invalid_end': _(u'Enter a valid end value.'),
    }

    def __init__(self, field_class, widget=forms.TextInput, *args, **kwargs):
        if 'initial' not in kwargs:
            kwargs['initial'] = ['', '']

        fields = (field_class(), field_class())

        super(RangeField, self).__init__(
                fields=fields,
                widget=RangeWidget(widget),
                *args, **kwargs
                )

    def compress(self, data_list):
        if data_list:
            return [self.fields[0].clean(data_list[0]), self.fields[1].clean(data_list[1])]

        return None
