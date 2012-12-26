"""
switchboard.models
~~~~~~~~~~~~~

:copyright: (c) 2012 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from datetime import datetime

from ming import Field, Session, schema
from ming.declarative import Document

from switchboard.settings import settings

DISABLED = 1
SELECTIVE = 2
GLOBAL = 3
INHERIT = 4

INCLUDE = 'i'
EXCLUDE = 'e'

NoValue = object()


class Switch(Document):
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

    class __mongometa__:
        session = Session.by_name('gutenberg')
        name = 'switchboard_switches'

    STATUS_CHOICES = (
        (DISABLED, 'Disabled'),
        (SELECTIVE, 'Selective'),
        (GLOBAL, 'Global'),
        (INHERIT, 'Inherit'),
    )

    STATUS_LABELS = {
        INHERIT: 'Inherit from parent',
        GLOBAL: 'Active for everyone',
        SELECTIVE: 'Active for conditions',
        DISABLED: 'Disabled for everyone',
    }

    # fields
    _id = Field(schema.ObjectId)
    key = Field(str)
    value = Field(None, if_missing=dict())
    label = Field(str)
    _date_created = Field('date_created', datetime,
                          if_missing=datetime.utcnow)
    _date_modified = Field('date_updated', datetime,
                           if_missing=datetime.utcnow)
    description = Field(str)
    status = Field(int, if_missing=DISABLED)

    def __init__(self, *args, **kwargs):
        params = args[0] if args else None
        if (
            params and
            hasattr(settings, 'SWITCHBOARD_SWITCH_DEFAULTS') and
            'key' in params and
            'status' not in params
        ):
            key = params['key']
            switch_default = settings.SWITCHBOARD_SWITCH_DEFAULTS.get(key)
            if switch_default is not None:
                is_active = switch_default.get('is_active')
                if is_active is True:
                    params['status'] = GLOBAL
                elif is_active is False:
                    params['status'] = DISABLED
                if not params.get('label'):
                    params['label'] = switch_default.get('label')
                if not params.get('description'):
                    params['description'] = switch_default.get('description')

        return super(Switch, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'%s=%s' % (self.key, self.value)

    def to_dict(self, manager):
        data = {
            'key': self.key,
            'status': self.status,
            'status_label': self.get_status_label(),
            'label': self.label or self.key.title(),
            'description': self.description,
            'date_modified': self._date_modified,
            'date_created': self._date_created,
            'conditions': [],
        }

        last = None
        for condition_set_id, group, field, value, exclude\
            in self.get_active_conditions(manager):
            if not last or last['id'] != condition_set_id:
                if last:
                    data['conditions'].append(last)

                last = {
                    'id': condition_set_id,
                    'label': group,
                    'conditions': []
                }

            last['conditions'].append((field.name, value,
                                       field.display(value), exclude))
        if last:
            data['conditions'].append(last)
        return data

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
            self.m.save()

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
            self.m.save()

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
            self.m.save()

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

    @classmethod
    def create(cls, **kwargs):
        instance = cls(kwargs)
        instance.m.save()
        return instance
