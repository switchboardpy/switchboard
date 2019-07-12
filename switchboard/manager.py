"""
switchboard.manager
~~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
import logging

from .base import ModelDict
from .models import (
    Switch,
    DISABLED, SELECTIVE, GLOBAL, INHERIT,
    INCLUDE, EXCLUDE,
)
from .proxy import SwitchProxy
from .settings import settings, Settings
import six

log = logging.getLogger(__name__)
# These are (mostly) read-only module variables since we want it shared among
# any and all threads. The only exception to read-only is when they are
# populated on Switchboard startup (i.e., operator.register()).
registry = {}
registry_by_namespace = {}


def nested_config(config):
    cfg = {}
    token = 'switchboard.'
    for k, v in six.iteritems(config):
        if k.startswith(token):
            cfg[k.replace(token, '')] = v
    return cfg


def configure(config={}, datastore=None, nested=False):
    """
    Useful for when you need to control Switchboard's setup
    """
    if nested:
        config = nested_config(config)
    # Re-read settings to make sure we have everything.
    # XXX It would be really nice if we didn't need to do this.
    Settings.init(**config)

    if datastore:
        Switch.ds = datastore

    # Register the builtins
    __import__('switchboard.builtins')


class SwitchManager(ModelDict):
    DISABLED = DISABLED
    SELECTIVE = SELECTIVE
    GLOBAL = GLOBAL
    INHERIT = INHERIT

    INCLUDE = INCLUDE
    EXCLUDE = EXCLUDE

    def __init__(self, *args, **kwargs):
        # Inject args and kwargs that are known quantities; the SwitchManager
        # will always deal with the Switch model and so on.
        new_args = [Switch]
        for a in args:
            new_args.append(a)
        kwargs['key'] = 'key'
        kwargs['value'] = 'value'
        self.result_cache = None
        self.context = {}
        super(SwitchManager, self).__init__(*new_args, **kwargs)

    def __unicode__(self):  # pragma: nocover
        return "<%s: %s (%s)>" % (self.__class__.__name__,
                                  getattr(self, 'model', ''),
                                  list(registry.values()))

    def __getitem__(self, key):
        """
        Returns a SwitchProxy, rather than a Switch. It allows us to
        easily extend the Switches method and automatically include our
        manager instance.
        """
        return SwitchProxy(self, super(SwitchManager, self).__getitem__(key))

    def with_result_cache(func):
        """
        Decorator specifically for is_active.  If self.result_cache is set to a {}
        the is_active results will be cached for each set of params.
        """
        def inner(self, *args, **kwargs):
            dic = self.result_cache
            cache_key = None
            if dic is not None:
                cache_key = (args, tuple(sorted(kwargs.items())))
                try:
                    result = dic.get(cache_key)
                except TypeError as e:  # not hashable
                    log.debug('Switchboard result cache not active for this "%s" check due to: %s within args: %s',
                              args[0], e, repr(cache_key)[:200])
                    cache_key = None
                else:
                    if result is not None:
                        return result
            result = func(self, *args, **kwargs)
            if cache_key is not None:
                dic[cache_key] = result
            return result
        return inner

    @with_result_cache
    def is_active(self, key, *instances, **kwargs):
        """
        Returns ``True`` if any of ``instances`` match an active switch.
        Otherwise returns ``False``.

        >>> operator.is_active('my_feature', request) #doctest: +SKIP
        """
        try:
            default = kwargs.pop('default', False)

            # Check all parents for a disabled state
            parts = key.split(':')
            if len(parts) > 1:
                child_kwargs = kwargs.copy()
                child_kwargs['default'] = None
                result = self.is_active(':'.join(parts[:-1]), *instances,
                                        **child_kwargs)

                if result is False:
                    return result
                elif result is True:
                    default = result

            try:
                switch = self[key]
            except KeyError:
                # switch is not defined, defer to parent
                return default

            if switch.status == GLOBAL:
                return True
            elif switch.status == DISABLED:
                return False
            elif switch.status == INHERIT:
                return default

            conditions = switch.value
            # If no conditions are set, we inherit from parents
            if not conditions:
                return default

            instances = list(instances) if instances else []
            instances.extend(list(self.context.values()))

            # check each switch to see if it can execute
            return_value = False

            for namespace, condition in six.iteritems(conditions):
                condition_set = registry_by_namespace.get(namespace)
                if not condition_set:
                    continue
                result = condition_set.has_active_condition(condition,
                                                            instances)
                if result is False:
                    return False
                elif result is True:
                    return_value = True
        except:
            log.exception('Error checking if switch "%s" is active', key)
            return_value = False

        # there were no matching conditions, so it must not be enabled
        return return_value

    def register(self, condition_set):
        """
        Registers a condition set with the manager.

        >>> condition_set = MyConditionSet() #doctest: +SKIP
        >>> operator.register(condition_set) #doctest: +SKIP
        """

        if callable(condition_set):
            condition_set = condition_set()
        registry[condition_set.get_id()] = condition_set
        registry_by_namespace[condition_set.get_namespace()] = condition_set

    def unregister(self, condition_set):
        """
        Unregisters a condition set with the manager.

        >>> operator.unregister(condition_set) #doctest: +SKIP
        """
        if callable(condition_set):
            condition_set = condition_set()
        registry.pop(condition_set.get_id(), None)
        registry_by_namespace.pop(condition_set.get_namespace(), None)

    def get_condition_set_by_id(self, switch_id):
        """
        Given the identifier of a condition set (described in
        ConditionSet.get_id()), returns the registered instance.
        """
        return registry[switch_id]

    def get_condition_sets(self):
        """
        Returns a generator yielding all currently registered
        ConditionSet instances.
        """
        return six.itervalues(registry)

    def get_all_conditions(self):
        """
        Returns a generator which yields groups of lists of conditions.

        >>> for set_id, label, field in operator.get_all_conditions(): #doctest: +SKIP
        >>>     print "%(label)s: %(field)s" % (label, field.label) #doctest: +SKIP
        """
        cs = self.get_condition_sets()
        for condition_set in sorted(cs, key=lambda x: x.get_group_label()):
            group = six.text_type(condition_set.get_group_label())
            for field in six.itervalues(condition_set.fields):
                yield condition_set.get_id(), group, field


auto_create = getattr(settings, 'SWITCHBOARD_AUTO_CREATE', True)
operator = SwitchManager(auto_create=auto_create)
