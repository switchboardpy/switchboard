"""
switchboard.admin
~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from datetime import datetime
import logging
from operator import attrgetter

from bottle import Bottle, request, mako_view as view
from webob.exc import HTTPNotFound

from .. import operator, signals
from ..helpers import MockCollection
from ..models import Switch
from .utils import (
    json_api,
    SwitchboardException,
    valid_sort_orders
)
from ..settings import settings
import six

log = logging.getLogger(__name__)


app = Bottle()
# Template poke-jiggery; will hopefully give way to config options soon.
import bottle
import os
dir_name = os.path.dirname(os.path.realpath(__file__))
bottle.TEMPLATE_PATH.append(dir_name)


@app.get('/')
@view('index')
def index():
    by = request.query.by or '-date_modified'
    if by not in valid_sort_orders():
        raise HTTPNotFound('Invalid sort order.')

    reverse = by.find('-') is 0
    sort_by = by.lstrip('-')

    switches = Switch.all()
    switches.sort(key=attrgetter(sort_by), reverse=reverse)

    messages = []
    if isinstance(Switch.c, MockCollection):
        m = dict(status='warning',
                 message='The datastore is in test mode, possibly due \
                         to an error with the real datastore.')
        messages.append(m)

    return dict(
        switches=[s.to_dict(operator) for s in switches],
        all_conditions=list(operator.get_all_conditions()),
        sorted_by=by,
        messages=messages,
        settings=settings,
    )


@app.post('/add')
@json_api
def add():
    key = request.forms['key']
    label = request.forms.get('label', '')
    description = request.forms.get('description')

    if not key:
        raise SwitchboardException("Key cannot be empty")

    if len(key) > 32:
        raise SwitchboardException("Key must be less than or equal to 32"
                                   + " characters in length")

    if len(label) > 32:
        raise SwitchboardException("Name must be less than or equal to 32"
                                   + " characters in length")

    if Switch.get(key=key):
        raise SwitchboardException("Switch with key %s already exists"
                                   % key)

    switch = Switch.create(key=key, label=label or None,
                           description=description)

    log.info('Switch %r added (%%s)' % switch.key,
             ', '.join('%s=%r' % (k, getattr(switch, k)) for k in
                       sorted(('key', 'label', 'description', ))))

    signals.switch_added.send(switch)
    return switch.to_dict(operator)


@app.post('/update')
@json_api
def update():
    curkey = request.forms['curkey']
    key = request.forms['key']
    label = request.forms.get('label', '')
    description = request.forms.get('description')

    switch = Switch.get(key=curkey)

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
    for k, v in six.iteritems(values):
        old_value = getattr(switch, k)
        if old_value != v:
            changes[k] = (v, old_value)

    if changes:
        if switch.key != key:
            switch.delete()
            switch.key = key

        switch.label = label
        switch.description = description
        switch.date_modified = datetime.utcnow()
        switch.save()

        log.info('Switch %r updated %%s' % switch.key,
                 ', '.join('%s=%r->%r' % (k, v[0], v[1]) for k, v in
                           sorted(six.iteritems(changes))))

        signals.switch_updated.send(switch)

    return switch.to_dict(operator)


@app.post('/status')
@json_api  # XXX Not needed?
def status():
    key = request.forms['key']
    status = request.forms['status']
    switch = Switch.get(key=key)

    try:
        status = int(status)
    except ValueError:
        raise SwitchboardException("Status must be integer")

    old_status_label = switch.get_status_display()

    if switch.status != status:
        switch.status = status
        switch.date_modified = datetime.utcnow()
        switch.save()

        log.info('Switch %r updated (status=%%s->%%s)' % switch.key,
                 old_status_label, switch.get_status_display())

        signals.switch_status_updated.send(switch)

    return switch.to_dict(operator)


@app.post('/delete')
@json_api
def delete():
    key = request.forms['key']
    switch = Switch.remove(key=key)
    log.info('Switch %r removed' % key)
    signals.switch_deleted.send(switch)
    return {}


@app.post('/add_condition')
@json_api
def add_condition():
    post = request.POST
    key = post.get("key")
    condition_set_id = post.get("id")
    field_name = post.get("field")
    exclude = int(post.get("exclude") or 0)

    if not all([key, condition_set_id, field_name]):
        raise SwitchboardException("Fields cannot be empty")

    condition_set = operator.get_condition_set_by_id(condition_set_id)
    field = condition_set.fields[field_name]
    value = field.validate(post)

    switch = operator[key]
    switch.add_condition(condition_set_id, field_name, value,
                         exclude=exclude)

    log.info('Condition added to %r (%r, %s=%r, exclude=%r)',
             switch.key, condition_set_id, field_name, value,
             bool(exclude))

    signals.switch_condition_added.send(switch)

    return switch.to_dict(operator)


@app.post('/remove_condition')
@json_api
def remove_condition():
    post = request.POST
    key = post.get("key")
    condition_set_id = post.get("id")
    field_name = post.get("field")
    value = post.get("value")

    if not all([key, condition_set_id, field_name, value]):
        raise SwitchboardException("Fields cannot be empty")

    switch = operator[key]
    switch.remove_condition(condition_set_id, field_name, value)

    log.info('Condition removed from %r (%r, %s=%r)' % (switch.key,
             condition_set_id, field_name, value))

    signals.switch_condition_removed.send(switch)

    return switch.to_dict(operator)


@app.get('/history')
@json_api
def history():
    key = request.query.key
    return Switch.get(key=key).list_versions()
