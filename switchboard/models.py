"""
switchboard.models
~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from datetime import datetime
import logging
import os
import uuid

from blinker import signal
import datastore.core
import datastore.filesystem

from .settings import settings
import six

log = logging.getLogger(__name__)

DISABLED = 1
SELECTIVE = 2
GLOBAL = 3
INHERIT = 4

INCLUDE = 'i'
EXCLUDE = 'e'

NAMESPACE = 'switchboard'


def _key(key=''):
    '''
    Returns a Datastore key object, prefixed with the NAMESPACE.
    '''
    if not isinstance(key, datastore.Key):
        # Switchboard uses ':' to denote one thing (parent-child) and datastore
        # uses it for another, so replace ':' in the datastore version of the
        # key.
        safe_key = key.replace(':', '|')
        key = datastore.Key(os.path.join(NAMESPACE, safe_key))
    return key


class Model(object):
    '''
    Basic data object for CRUD operations on top of a datastore.
    '''
    # Default to an in-memory datastore; can be set to an supported datastore
    # via the configure call. You can and should change this to a more robust
    # datastore, particularly one with caching, for production systems. See
    # http://datastore.readthedocs.io/en/latest/ for more details about what
    # all can be done with datastores.
    ds = datastore.DictDatastore()

    pre_save = signal('pre_save')
    post_save = signal('post_save')
    pre_delete = signal('pre_delete')
    post_delete = signal('post_delete')

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def save(self):
        # A little odd, but we need to see if a previous model has been
        # saved, e.g., in the case of an update operation.
        try:
            key = _key(self.key)
        except AttributeError:
            self.key = str(uuid.uuid4())
            key = _key(self.key)
            previous = None
        else:
            previous = self.get(key)
        self.pre_save.send(previous)
        self.ds.put(key, self.__dict__)
        self.post_save.send(self)
        return self.key

    def delete(self):
        return self.remove(self.key)

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        instance.save()
        return instance

    @classmethod
    def get(cls, key):
        key = _key(key)
        data = cls.ds.get(key)
        return cls(**data) if data else None

    @classmethod
    def contains(cls, key):
        key = _key(key)
        return cls.ds.contains(key)

    @classmethod
    def get_or_create(cls, key, defaults={}):
        '''
        A port of functionality from the Django ORM. Defaults can be passed in
        if creating a new document is necessary. Keyword args are used to
        lookup the document. Returns a tuple of (object, created), where object
        is the retrieved or created object and created is a boolean specifying
        whether a new object was created.
        '''
        instance = cls.get(key)
        if not instance:
            created = True
            data = dict(key=key)
            data.update(defaults)
            # Do an upsert here instead of a straight create to avoid a race
            # condition with another instance creating the same record at
            # nearly the same time.
            instance = cls.update(data, data, upsert=True)
        else:
            created = False
        return instance, created

    @classmethod
    def update(cls, spec, updates, upsert=False):
        '''
        The spec is used to search for the data to update, updates contains the
        values to be updated, and upsert specifies whether to do an insert if
        the original data is not found.
        '''
        if 'key' in spec:
            previous = cls.get(spec['key'])
        else:
            previous = None
        if previous:
            # Update existing data.
            current = cls(**previous.__dict__)
        elif upsert:
            # Create new data.
            current = cls(**spec)
        else:
            current = None
        # XXX Should there be any error thrown if this is a noop?
        if current:
            current.__dict__.update(updates)
            current.save()
        return current

    @classmethod
    def remove(cls, key):
        key = _key(key)
        instance = cls.get(key)
        if instance:
            cls.pre_delete.send(instance)
            result = cls.ds.delete(key)
            cls.post_delete.send(instance)
        else:
            # XXX Should there be any error thrown if this is a noop?
            result = None
        return result

    @classmethod
    def all(cls):
        query = datastore.Query(_key())
        try:
            results = cls.ds.query(query)
        except NotImplementedError:
            results = cls._queryless_all()
        return [cls(**result) for result in results]

    @classmethod
    def _queryless_all(cls):
        '''
        This is a hack because some datastore implementations don't support
        querying. Right now the solution is to drop down to the underlying
        native client and query all, which means that this section is ugly.
        If it were architected properly, you might be able to do something
        like inject an implementation of a NativeClient interface, which would
        let Switchboard users write their own NativeClient wrappers that
        implement all. However, at this point I'm just happy getting datastore
        to work, so quick-and-dirty will suffice.
        '''
        if hasattr(cls.ds, '_redis'):
            r = cls.ds._redis
            keys = list(r.keys())
            serializer = cls.ds.child_datastore.serializer

            def get_value(k):
                value = r.get(k)
                return value if value is None else serializer.loads(value)
            return [get_value(k) for k in keys]
        else:
            raise NotImplementedError

    @classmethod
    def drop(cls):
        for m in cls.all():
            m.delete()

    @classmethod
    def count(cls):
        return len(cls.ds)


class Switch(Model):
    """
    Stores information on all switches. Generally handled under the global
    ``switchboard`` namespace.

    ``value`` is stored with by type label, and then by column:

    >>> {
    >>>   namespace: {
    >>>       id: [[INCLUDE, 0, 50], [INCLUDE, 'string']] // 50% of users
    >>>   }
    >>> }
    """

    STATUS_CHOICES = {
        INHERIT: 'Inherit',
        GLOBAL: 'Global',
        SELECTIVE: 'Selective',
        DISABLED: 'Disabled',
    }

    STATUS_LABELS = {
        INHERIT: 'Inherit from parent',
        GLOBAL: 'Active for everyone',
        SELECTIVE: 'Active for conditions',
        DISABLED: 'Disabled for everyone',
    }

    def __init__(self, *args, **kwargs):
        if (
            kwargs and
            hasattr(settings, 'SWITCHBOARD_SWITCH_DEFAULTS') and
            'key' in kwargs and
            'status' not in kwargs
        ):
            key = kwargs['key']
            switch_default = settings.SWITCHBOARD_SWITCH_DEFAULTS.get(key)
            if switch_default is not None:
                is_active = switch_default.get('is_active')
                if is_active is True:
                    kwargs['status'] = GLOBAL
                elif is_active is False:
                    kwargs['status'] = DISABLED
                if not kwargs.get('label'):
                    kwargs['label'] = switch_default.get('label')
                if not kwargs.get('description'):
                    kwargs['description'] = switch_default.get('description')
        self.value = kwargs.get('value', {})
        self.label = kwargs.get('label', '')
        self.date_created = kwargs.get('date_created', datetime.utcnow())
        self.date_modified = kwargs.get('date_modified', datetime.utcnow())
        self.description = kwargs.get('description', '')
        self.status = kwargs.get('status', DISABLED)
        # Parent constructor will handle kwargs like "key" that don't have
        # default values.
        super(Switch, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return '%s=%s' % (self.key, self.value)

    def get_status_display(self):
        return self.STATUS_CHOICES[self.status]

    def add_condition(self, manager, condition_set, field_name, condition,
                      exclude=False, commit=True):
        """
        Adds a new condition and registers it in the global ``operator`` switch
        manager.

        If ``commit`` is ``False``, the data will not be written to the
        database.

        >>> switch = operator['my_switch'] #doctest: +SKIP
        >>> cs_id = condition_set.get_id() #doctest: +SKIP
        >>> switch.add_condition(cs_id, 'percent', [0, 50]) #doctest: +SKIP
        """
        condition_set = manager.get_condition_set_by_id(condition_set)

        assert isinstance(condition, six.string_types), 'conditions must be strings'

        namespace = condition_set.get_namespace()

        if namespace not in self.value:
            self.value[namespace] = {}
        if field_name not in self.value[namespace]:
            self.value[namespace][field_name] = []
        if condition not in self.value[namespace][field_name]:
            self.value[namespace][field_name].append([exclude
                                                      and EXCLUDE
                                                      or INCLUDE,
                                                      condition])

        if commit:
            self.save()

    def remove_condition(self, manager, condition_set, field_name, condition,
                         commit=True):
        """
        Removes a condition and updates the global ``operator`` switch manager.

        If ``commit`` is ``False``, the data will not be written to the
        database.

        >>> switch = operator['my_switch'] #doctest: +SKIP
        >>> cs_id = condition_set.get_id() #doctest: +SKIP
        >>> switch.remove_condition(cs_id, 'percent', [0, 50]) #doctest: +SKIP
        """
        condition_set = manager.get_condition_set_by_id(condition_set)

        namespace = condition_set.get_namespace()

        if namespace not in self.value:
            return

        if field_name not in self.value[namespace]:
            return

        conditions = self.value[namespace][field_name]
        self.value[namespace][field_name] = ([c for c in conditions
                                             if c[1] != condition])

        if not self.value[namespace][field_name]:
            del self.value[namespace][field_name]

            if not self.value[namespace]:
                del self.value[namespace]

        if commit:
            self.save()

    def clear_conditions(self, manager, condition_set, field_name=None,
                         commit=True):
        """
        Clears conditions given a set of parameters.

        If ``commit`` is ``False``, the data will not be written to the
        database.

        Clear all conditions given a ConditionSet, and a field name:

        >>> switch = operator['my_switch'] #doctest: +SKIP
        >>> cs_id = condition_set.get_id() #doctest: +SKIP
        >>> switch.clear_conditions(cs_id, 'percent') #doctest: +SKIP

        You can also clear all conditions given a ConditionSet:

        >>> switch = operator['my_switch'] #doctest: +SKIP
        >>> cs_id = condition_set.get_id() #doctest: +SKIP
        >>> switch.clear_conditions(cs_id) #doctest: +SKIP
        """
        condition_set = manager.get_condition_set_by_id(condition_set)

        namespace = condition_set.get_namespace()

        if namespace not in self.value:
            return

        if not field_name:
            del self.value[namespace]
        elif field_name not in self.value[namespace]:
            return
        else:
            del self.value[namespace][field_name]

        if commit:
            self.save()

    def get_active_conditions(self, manager):
        '''
        Returns a generator which yields groups of lists of conditions.

        >>> conditions = switch.get_active_conditions()
        >>> for label, set_id, field, value, exc in conditions: #doctest: +SKIP
        >>>     print ("%(label)s: %(field)s = %(value)s (exclude: %(exc)s)"
        >>>            % (label, field.label, value, exc)) #doctest: +SKIP
        '''
        for condition_set in sorted(manager.get_condition_sets(),
                                    key=lambda x: x.get_group_label()):
            ns = condition_set.get_namespace()
            condition_set_id = condition_set.get_id()
            if ns in self.value:
                group = condition_set.get_group_label()
                for name, field in six.iteritems(condition_set.fields):
                    for value in self.value[ns].get(name, []):
                        try:
                            yield (condition_set_id, group, field, value[1],
                                   value[0] == EXCLUDE)
                        except TypeError:
                            continue

    def get_status_label(self):
        if self.status == SELECTIVE and not self.value:
            status = GLOBAL
        else:
            status = self.status

        return self.STATUS_LABELS[status]

    def to_dict(self, manager):
        data = {
            'key': self.key,
            'status': self.status,
            'status_label': self.get_status_label(),
            'label': self.label or self.key.title(),
            'description': self.description,
            'date_modified': self.date_modified,
            'date_created': self.date_created,
            'conditions': [],
        }

        last = None
        actives = self.get_active_conditions(manager)
        for set_id, group, field, value, exclude in actives:
            if not last or last['id'] != set_id:
                if last:
                    data['conditions'].append(last)

                last = {
                    'id': set_id,
                    'label': group,
                    'conditions': []
                }

            last['conditions'].append((field.name, value,
                                       field.display(value), exclude))
        if last:
            data['conditions'].append(last)
        return data
