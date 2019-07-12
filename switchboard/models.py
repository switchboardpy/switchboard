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

from blinker import signal
from pymongo import DESCENDING

from .settings import settings
from .helpers import MockCollection
import six

log = logging.getLogger(__name__)

DISABLED = 1
SELECTIVE = 2
GLOBAL = 3
INHERIT = 4

INCLUDE = 'i'
EXCLUDE = 'e'


class MongoModel(object):
    # May be lazy initialized to a real Mongo connection by calling
    # switchboard.configure()
    c = MockCollection()

    pre_save = signal('pre_save')
    post_save = signal('post_save')
    pre_delete = signal('pre_delete')
    post_delete = signal('post_delete')

    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

    def to_bson(self):
        # Return a copy so that any subsequent operations don't end up changing
        # this object.
        return self.__dict__.copy()

    def save(self):
        if hasattr(self, '_id'):
            previous = self.get(_id=self._id)
        else:
            previous = None
        self.pre_save.send(previous)
        _id = self.c.save(self.to_bson())
        if not hasattr(self, '_id'):
            self._id = _id
        self.post_save.send(self)
        return _id

    def delete(self):
        return self.remove(key=self.key)

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        instance.save()
        return instance

    @classmethod
    def get(cls, **kwargs):
        result = cls.c.find_one(kwargs)
        return cls(**result) if result else None

    @classmethod
    def get_or_create(cls, defaults={}, **kwargs):
        '''
        A port of functionality from the Django ORM. Defaults can be passed in
        if creating a new document is necessary. Keyword args are used to
        lookup the document. Returns a tuple of (object, created), where object
        is the retrieved or created object and created is a boolean specifying
        whether a new object was created.
        '''
        result = cls.c.find_one(kwargs)
        if not result:
            created = True
            result = kwargs
            result.update(defaults)
            # Do an upsert here instead of a straight create to avoid a race
            # condition with another instance creating the same record at
            # nearly the same time.
            cls.update(result, result, upsert=True)
            result = cls.c.find_one(kwargs)
            instance = cls(**result)
        else:
            created = False
            instance = cls(**result)
        return instance, created

    @classmethod
    def find(cls, **kwargs):
        return [cls(**s) for s in cls.c.find(kwargs)]

    @classmethod
    def update(cls, spec, document, upsert=False):
        '''
        Mimics a subset of PyMongo's Collection.update functionality. The spec
        is used to search for the document to update, document contains the
        values to be updated, and upsert specifies whether to do an insert if
        the original document is not found.
        '''
        previous = cls.get(**spec)
        cls.pre_save.send(previous)
        result = cls.c.update(spec, document, upsert=upsert)
        current = cls.get(**spec)
        cls.post_save.send(current)
        return result

    @classmethod
    def remove(cls, **kwargs):
        instance = cls.get(**kwargs)
        cls.pre_delete.send(instance)
        result = cls.c.remove(kwargs)
        cls.post_delete.send(instance)
        return result

    @classmethod
    def all(cls):
        return [cls(**s) for s in cls.c.find()]

    @classmethod
    def count(cls):
        return cls.c.count()


class VersioningMongoModel(MongoModel):

    def __init__(self, *args, **kwargs):
        super(VersioningMongoModel, self).__init__(*args, **kwargs)

    @classmethod
    def _versioned_collection(cls):
        return cls.c.database[cls.c.name + '.versions']

    def _diff(self):
        # Need to verify that the data contained in self is actually still in
        # the collection
        if hasattr(self, '_id'):
            curr = self.get(_id=self._id)
            curr = curr.to_bson() if curr else None
        else:
            curr = None
        prev = self.previous_version()
        prev = prev.to_bson() if prev else None
        # Both models are present so something's changed between them
        if prev and curr:
            current_fields = list(curr.keys())
            previous_fields = list(prev.keys())
            added = [f for f in current_fields if f not in previous_fields]
            deleted = [f for f in previous_fields if f not in current_fields]
            changed = [f for f in current_fields if (f in previous_fields
                                                     and prev[f] != curr[f])]
            delta = dict(
                added=dict([(k, curr[k]) for k in added]),
                deleted=dict([(k, prev[k]) for k in deleted]),
                changed=dict([(k, (prev[k], curr[k])) for k in changed]),
            )
        elif prev:  # Model's been deleted
            delta = dict(
                added={},
                deleted=prev,
                changed={},
            )
        elif curr:  # Model's been added
            delta = dict(
                added=curr,
                deleted={},
                changed={},
            )
        else:       # Neither model exists, no-op
            delta = dict(
                added={},
                deleted={},
                changed={},
            )
        return delta

    def save_version(self, **kwargs):
        delta = self._diff()
        # if nothing changed, don't save anything
        if delta and (delta['added'] or delta['deleted'] or delta['changed']):
            doc = dict(
                switch_id=self._id,
                timestamp=datetime.utcnow(),
                delta=delta,
                **kwargs
            )
            self._versioned_collection().save(doc)

    def _unpack_delta(self, version):
        '''
        Helper function that makes it easier to access the data nested with a
        delta. Returns a tuple of (delta, added, deleted, changed).
        '''
        delta = version.get('delta', {})
        added = delta.get('added', {})
        deleted = delta.get('deleted', {})
        changed = delta.get('changed', {})
        return delta, added, deleted, changed

    def previous_version(self):
        if not hasattr(self, '_id'):
            return self.__class__()
        vc = self._versioned_collection()
        versions = vc.find(dict(switch_id=self._id))
        previous = dict()
        # build up the previous state based on all past deltas
        if versions:
            # Before sorting, ensure we're working with a list and not a cursor
            # or other iterable.
            versions = list(versions)
            versions.sort(key=lambda x: x['timestamp'])
            for v in versions:
                delta, added, deleted, changed = self._unpack_delta(v)
                previous.update(added)
                for k in deleted.keys():
                    if k in previous:
                        del previous[k]
                for k, v in six.iteritems(changed):
                    old, new = v
                    previous[k] = new
        previous = self.__class__(**previous) if previous else None
        return previous


class Switch(VersioningMongoModel):
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

        self.key = kwargs.get('key')
        self.value = kwargs.get('value', {})
        self.label = kwargs.get('label', '')
        self.date_created = kwargs.get('date_created', datetime.utcnow())
        self.date_modified = kwargs.get('date_modified', datetime.utcnow())
        self.description = kwargs.get('description', '')
        self.status = kwargs.get('status', DISABLED)
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

    # TODO: Consolidate to_bson and to_dict; they should be the same. It should
    # be as simple as spitting out __dict__.
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

    def list_versions(self):
        '''
        Return a display-friendly list of all versions.
        '''
        vc = self._versioned_collection()
        versions = vc.find(dict(switch_id=self._id))
        if not versions:
            return dict(versions={})
        return list(versions.sort('timestamp', DESCENDING))
