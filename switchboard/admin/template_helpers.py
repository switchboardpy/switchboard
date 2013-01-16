"""
switchboard.admin.template_helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 SourceForge.
:license: Apache License 2.0, see LICENSE for more details.
"""


def render_field(field, value=None):
    return field.render(value)


def sort_by_key(field, currently):
    is_negative = currently.find('-') is 0
    current_field = currently.lstrip('-')

    if current_field == field and is_negative:
        return field
    elif current_field == field:
        return '-' + field
    else:
        return field


def sort_field(sort_string):
    return sort_string.lstrip('-')

jinja_filters = dict(
    render_field=render_field,
    sort_by_key=sort_by_key,
    sort_field=sort_field,
)
