"""
switchboard.admin.controllers
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 SourceForge.
:license: Apache License 2.0, see LICENSE for more details.
"""

import logging
from decorator import decorator
from datetime import datetime

from webob.exc import HTTPNotFound
from tg import expose
from tg.decorators import with_trailing_slash
import pymongo

from switchboard import operator
from switchboard.models import Switch
from switchboard.conditions import Invalid
from switchboard.settings import settings


log = logging.getLogger(__name__)


class SwitchboardException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


@decorator
def json_api(func, *args, **kwargs):
    "Decorator to make JSON views simpler"
    try:
        response = {
            "success": True,
            "data": func(*args, **kwargs)
        }
    except SwitchboardException, exc:
        response = {
            "success": False,
            "data": exc.message
        }
    except ValueError:
        response = {
            "success": False,
            "data": "Switch cannot be found"
        }
    except Invalid, e:
        response = {
            "success": False,
            "data": u','.join(map(unicode, e.messages)),
        }
    except Exception:
        if hasattr(settings, 'DEBUG') and settings.DEBUG:
            import traceback
            traceback.print_exc()
        raise
    return response


class SwitchboardController(object):
    @with_trailing_slash
    @expose('switchboard_index.html')
    def index(self, by='-date_modified'):
        if by not in self.valid_sort_orders:
            raise HTTPNotFound('Invalid sort order.')

        is_negative = by.find('-') is 0
        order = pymongo.DESCENDING if is_negative else pymongo.ASCENDING
        sort_by = by.lstrip('-')

        switches = Switch.m.find().sort(sort_by, order).all()

        return dict(
            switches=[s.to_dict(operator) for s in switches],
            all_conditions=list(operator.get_all_conditions()),
            sorted_by=by
        )

    @expose('json')
    @json_api
    def add(self, key, label='', description=None, **kwargs):
        if not key:
            raise SwitchboardException("Key cannot be empty")

        if len(key) > 32:
            raise SwitchboardException("Key must be less than or equal to 32"
                                       + " characters in length")

        if len(label) > 32:
            raise SwitchboardException("Name must be less than or equal to 32"
                                       + " characters in length")

        log.debug("Count for %s: %s", key, Switch.m.find(key=key).count())
        if Switch.m.find(dict(key=key)).count():
            raise SwitchboardException("Switch with key %s already exists"
                                       % key)

        switch = Switch(dict(
            key=key,
            label=label or None,
            description=description
        ))
        switch.m.save()

        log.info('Switch %r added (%%s)' % switch.key,
                 ', '.join('%s=%r' % (k, getattr(switch, k)) for k in
                           sorted(('key', 'label', 'description', ))))

        operator[key] = switch
        return switch.to_dict(operator)

    @expose('json')
    @json_api
    def update(self, curkey, key, label='', description=None):
        switch = Switch.m.get(key=curkey)

        if len(key) > 32:
            raise SwitchboardException("Key must be less than or equal to 32"
                                       + " characters in length")

        if len(label) > 32:
            raise SwitchboardException("Name must be less than or equal to 32"
                                       + " characters in length")

        values = dict(
            label=label,
            key=key,
            description=description,
        )

        changes = {}
        for k, v in values.iteritems():
            old_value = getattr(switch, k)
            if old_value != v:
                changes[k] = (v, old_value)

        if changes:
            if switch.key != key:
                switch.m.delete()
                switch.key = key

            switch.label = label
            switch.description = description
            switch.date_modified = datetime.utcnow()
            switch.m.save()

            log.info('Switch %r updated %%s' % switch.key,
                     ', '.join('%s=%r->%r' % (k, v[0], v[1]) for k, v in
                               sorted(changes.iteritems())))

        operator[key] = switch
        return switch.to_dict(operator)

    @expose('json')
    @json_api
    def status(self, key, status):
        switch = Switch.m.get(key=key)

        try:
            status = int(status)
        except ValueError:
            raise SwitchboardException("Status must be integer")

        old_status_label = switch.get_status_display()

        if switch.status != status:
            switch.status = status
            switch.date_modified = datetime.utcnow()
            switch.m.save()

            log.info('Switch %r updated (status=%%s->%%s)' % switch.key,
                     old_status_label, switch.get_status_display())

        operator[key] = switch
        return switch.to_dict(operator)

    @expose('json')
    @json_api
    def delete(self, key):
        switch = Switch.m.get(key=key)
        switch.m.delete()

        log.info('Switch %r removed' % switch.key)

        if key in operator:
            del operator[key]
        return {}

    @expose('json')
    @json_api
    def add_condition(self, *args, **kwargs):
        key = kwargs.get("key")
        condition_set_id = kwargs.get("id")
        field_name = kwargs.get("field")
        exclude = int(kwargs.get("exclude") or 0)

        if not all([key, condition_set_id, field_name]):
            raise SwitchboardException("Fields cannot be empty")

        condition_set = operator.get_condition_set_by_id(condition_set_id)
        field = condition_set.fields[field_name]
        value = field.validate(kwargs)

        switch = operator[key]
        switch.add_condition(condition_set_id, field_name, value,
                             exclude=exclude)

        log.info('Condition added to %r (%r, %s=%r, exclude=%r)',
                 switch.key, condition_set_id, field_name, value,
                 bool(exclude))

        operator[key] = switch
        return switch.to_dict(operator)

    @expose('json')
    @json_api
    def remove_condition(self, *args, **kwargs):
        key = kwargs.get("key")
        condition_set_id = kwargs.get("id")
        field_name = kwargs.get("field")
        value = kwargs.get("value")

        if not all([key, condition_set_id, field_name, value]):
            raise SwitchboardException("Fields cannot be empty")

        switch = operator[key]
        switch.remove_condition(condition_set_id, field_name, value)

        log.info('Condition removed from %r (%r, %s=%r)' % (switch.key,
                 condition_set_id, field_name, value))

        operator[key] = switch
        return switch.to_dict(operator)

    @property
    def valid_sort_orders(self):
        fields = ['label', 'date_created', 'date_modified']
        return fields + ['-' + f for f in fields]
