"""
switchboard.admin.jinja_helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 SourceForge.
:license: Apache License 2.0, see LICENSE for more details.
"""
from datetime import datetime


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


def timesince(dt):
    delta = datetime.utcnow() - dt
    days = delta.days + float(delta.seconds) / 86400
    if days > 1:
        return '%d days' % round(days)
    # since days is < 1, a fraction, we multiply to get hours
    hours = days * 24
    if hours > 1:
        return '%d hours' % round(hours)
    minutes = hours * 60
    if minutes > 1:
        return '%d minutes' % round(minutes)
    seconds = minutes * 60
    return '%d seconds' % round(seconds)
