"""
switchboard.models
~~~~~~~~~~~~~

:copyright: (c) 2012 SourceForge.
:license: Apache License 2.0, see LICENSE for more details.
"""

from datetime import datetime
import logging

from blinker import signal

from .settings import settings
from .helpers import MockCollection

log = logging.getLogger(__name__)

DISABLED = 1
SELECTIVE = 2
GLOBAL = 3
INHERIT = 4

INCLUDE = 'i'
EXCLUDE = 'e'

post_save = signal('post_save')
post_delete = signal('post_delete')


class MongoModel(object):
    # May be lazy initialized to a real Mongo connection by calling
    # switchboard.configure()
    c = MockCollection()

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def to_bson(self):
        raise NotImplementedError

    def save(self, created=False):
        _id = self.c.save(self.to_bson())
        if created:
            self._id = _id
        post_save.send(self, created=created)
        return _id

    def delete(self):
        return self.remove(key=self.key)

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        instance.save(created=True)
        return instance

    @classmethod
    def get(cls, **kwargs):
        result = cls.c.find_one(kwargs)
        return cls(**result) if result else None

    @classmethod
    def get_or_create(cls, defaults={}, **kwargs):
        result = cls.c.find_one(kwargs)
        if not result:
            created = True
            result = kwargs
            result.update(defaults)
            instance = cls.create(**result)
        else:
            created = False
            instance = cls(**result)
        return instance, created

    @classmethod
    def find(cls, **kwargs):
        return [cls(**s) for s in cls.c.find(kwargs)]

    @classmethod
    def update(cls, spec, document):
        result = cls.c.update(spec, document)
        instance = cls.get(**spec)
        post_save.send(instance, created=False)
        return result

    @classmethod
    def remove(cls, **kwargs):
        instance = cls.get(**kwargs)
        result = cls.c.remove(kwargs)
        post_delete.send(instance)
        return result

    @classmethod
    def all(cls):
        return [cls(**s) for s in cls.c.find()]

    @classmethod
    def count(cls):
        return cls.c.count()


class Switch(MongoModel):
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

        if '_id' in kwargs:
            self._id = kwargs['_id']
        self.key = kwargs.get('key')
        self.value = kwargs.get('value', {})
        self.label = kwargs.get('label', '')
        self.date_created = kwargs.get('date_created', datetime.utcnow())
        self.date_modified = kwargs.get('date_modified', datetime.utcnow())
        self.description = kwargs.get('description', '')
        self.status = kwargs.get('status', DISABLED)

    def __unicode__(self):
        return u'%s=%s' % (self.key, self.value)

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
        >>> condition_set_id = condition_set.get_id() #doctest: +SKIP
        >>> switch.add_condition(condition_set_id, 'percent', [0, 50], exclude=False) #doctest: +SKIP
        """
        condition_set = manager.get_condition_set_by_id(condition_set)

        assert isinstance(condition, basestring), 'conditions must be strings'

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
        >>> condition_set_id = condition_set.get_id() #doctest: +SKIP
        >>> switch.remove_condition(condition_set_id, 'percent', [0, 50]) #doctest: +SKIP
        """
        condition_set = manager.get_condition_set_by_id(condition_set)

        namespace = condition_set.get_namespace()

        if namespace not in self.value:
            return

        if field_name not in self.value[namespace]:
            return

        self.value[namespace][field_name] = ([c for c
            in self.value[namespace][field_name] if c[1] != condition])

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
        >>> condition_set_id = condition_set.get_id() #doctest: +SKIP
        >>> switch.clear_conditions(condition_set_id, 'percent') #doctest: +SKIP

        You can also clear all conditions given a ConditionSet:

        >>> switch = operator['my_switch'] #doctest: +SKIP
        >>> condition_set_id = condition_set.get_id() #doctest: +SKIP
        >>> switch.clear_conditions(condition_set_id) #doctest: +SKIP
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
        """
        Returns a generator which yields groups of lists of conditions.

        >>> for label, set_id, field, value, exclude in gargoyle.get_all_conditions(): #doctest: +SKIP
        >>>     print "%(label)s: %(field)s = %(value)s (exclude: %(exclude)s)" % (label, field.label, value, exclude) #doctest: +SKIP
        """
        for condition_set in sorted(manager.get_condition_sets(), key=lambda x: x.get_group_label()):
            ns = condition_set.get_namespace()
            condition_set_id = condition_set.get_id()
            if ns in self.value:
                group = condition_set.get_group_label()
                for name, field in condition_set.fields.iteritems():
                    for value in self.value[ns].get(name, []):
                        try:
                            yield condition_set_id, group, field, value[1], value[0] == EXCLUDE
                        except TypeError:
                            continue

    def get_status_label(self):
        if self.status == SELECTIVE and not self.value:
            status = GLOBAL
        else:
            status = self.status

        return self.STATUS_LABELS[status]

    # TODO: Consolidate to_bson and to_dict; they should be the same.
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

    def to_bson(self):
        data = dict(
            key=self.key,
            status=self.status,
            label=self.label,
            description=self.description,
            date_created=self.date_created,
            date_modified=self.date_modified,
            value=self.value
        )
        if hasattr(self, '_id'):
            data['_id'] = self._id
        return data
