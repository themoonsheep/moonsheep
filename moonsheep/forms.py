import re

from django import forms
from django.core.validators import RegexValidator, ValidationError


class NewTaskForm(forms.Form):
    url = forms.URLField(label="Report URL")


class MultipleRangeField(forms.CharField):
    default_validators = [RegexValidator(regex="[\w\d]+[\w]?(-[\w\d]+[\w]?)?(,[\w\d]+[\w]?(-[\w\d]+[\w]?)?)*")]

    def to_python(self, value):
        values = []

        # Search for invalid space occurrences, i.e. " 1 1, 2-3, 1 1-2"
        no_spaces = value.split(" ")
        while "" in no_spaces:
            no_spaces.remove("")
        for idx, val in enumerate(no_spaces):
            if len(no_spaces) > idx + 1 and re.match("^\d+$", val) and re.match("^\d+$", no_spaces[idx+1]):
                raise ValidationError("Cannot divide tokens (IDs) by space. Use comma instead.")
        # Remove spaces
        value = value.replace(" ", "")
        # Split value in sections divided by comma, i.e. "1", "3-6", "a23", "a1-a6"
        sections = value.split(",")
        for section in sections:
            # Split ranges in sections
            section_range = section.split("-")
            # If ranges have more than 2 parts, then raise error, i.e. "1-5-10"
            if len(section_range) > 2:
                raise ValidationError("Wrong range format.")
            # Change ranges into lists
            elif len(section_range) == 2:
                if not section_range[0][-1].isnumeric() or not section_range[1][-1].isnumeric():
                    raise ValidationError(
                        "Wrong suffix format. Letters may be used only as prefix in range, i.e. A1-A3."
                    )
                # Remove prefixes for range iteration
                prefix_0 = ""
                while section_range and not section_range[0][0].isnumeric():
                    prefix_0 += section_range[0][0]
                    section_range[0] = section_range[0][1:]
                prefix_1 = ""
                while section_range and not section_range[1][0].isnumeric():
                    prefix_1 += section_range[1][0]
                    section_range[1] = section_range[1][1:]
                # Compare prefixes. They must be the same
                if prefix_0 != prefix_1:
                    raise ValidationError("Prefixes must be the same, i.e. A1-A3")
                try:
                    v_start = int(section_range[0])
                    v_end = int(section_range[1])
                except ValueError:
                    raise ValidationError(
                        "Wrong suffix format. Letters may be used only as prefix in range, i.e. A1-A3."
                    )
                # Check if can be iterated
                if v_start > v_end:
                    raise ValidationError("Reverse range. Should be {lower_value}-{greater_value}.")
                # Iterate, add back prefixes
                for v in range(v_start, v_end + 1):
                    token = prefix_0 + str(v)
                    if token not in values:
                        values.append(token)
            # one element
            elif len(section_range) == 1:
                if section_range[0] not in values:
                    values.append(section_range[0])
            # neighbouring commas ",,"
            else:
                raise ValidationError("Too many commas - \",,\"")
        return values
