from webob import Request
from paste.registry import StackedObjectProxy

from switchboard.models import (
    Switch,
    DISABLED, SELECTIVE, GLOBAL, INHERIT,
    INCLUDE, EXCLUDE
)
from switchboard.proxy import SwitchProxy
from switchboard.settings import settings


class SwitchManager(dict):
    DISABLED = DISABLED
    SELECTIVE = SELECTIVE
    GLOBAL = GLOBAL
    INHERIT = INHERIT

    INCLUDE = INCLUDE
    EXCLUDE = EXCLUDE

    def __init__(self, auto_create=False, *args, **kwargs):
        self.auto_create = auto_create
        # We'll store available conditions in the registry
        self._registry = {}
        super(SwitchManager, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self._registry.values())

    def __getitem__(self, key):
        """
        Returns a SwitchProxy, rather than a Switch. It allows us to
        easily extend the Switches method and automatically include our
        manager instance.
        """
        switch = self.get(key)
        if not switch:
            switch = Switch.m.get(key=key)
            if not switch and self.auto_create:
                switch = Switch.create(key=key)
            if not switch:
                raise KeyError
            self[key] = switch
        return SwitchProxy(self, switch)

    def __setitem__(self, key, value):
        # Make sure we're storing a switch and not a proxy
        if isinstance(value, SwitchProxy):
            value = value._switch
        super(SwitchManager, self).__setitem__(key, value)

    def is_active(self, key, *instances, **kwargs):
        """
        Returns ``True`` if any of ``instances`` match an active switch.
        Otherwise returns ``False``.

        >>> opersator.is_active('my_feature', request) #doctest: +SKIP
        """
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

        if instances:
            instances = list(instances)
            for v in instances:
                # HACK: support request.user by swapping in User instance
                if isinstance(v, Request) and hasattr(v, 'user'):
                    instances.append(v.user)
                # HACK: unwrapped objects inside a proxy
                if isinstance(v, StackedObjectProxy):
                    instances.append(v._current_obj())

        # check each switch to see if it can execute
        return_value = False

        for switch in self._registry.itervalues():
            result = switch.has_active_condition(conditions, instances)
            if result is False:
                return False
            elif result is True:
                return_value = True

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
        self._registry[condition_set.get_id()] = condition_set

    def unregister(self, condition_set):
        """
        Unregisters a condition set with the manager.

        >>> operator.unregister(condition_set) #doctest: +SKIP
        """
        if callable(condition_set):
            condition_set = condition_set()
        self._registry.pop(condition_set.get_id(), None)

    def get_condition_set_by_id(self, switch_id):
        """
        Given the identifier of a condition set (described in
        ConditionSet.get_id()), returns the registered instance.
        """
        return self._registry[switch_id]

    def get_condition_sets(self):
        """
        Returns a generator yielding all currently registered
        ConditionSet instances.
        """
        return self._registry.itervalues()

    def get_all_conditions(self):
        """
        Returns a generator which yields groups of lists of conditions.

        >>> for set_id, label, field in operator.get_all_conditions(): #doctest: +SKIP
        >>>     print "%(label)s: %(field)s" % (label, field.label) #doctest: +SKIP
        """
        cs = self.get_condition_sets()
        for condition_set in sorted(cs, key=lambda x: x.get_group_label()):
            group = unicode(condition_set.get_group_label())
            for field in condition_set.fields.itervalues():
                yield condition_set.get_id(), group, field

    def as_request(self, user=None, ip_address=None):
        from switchboard.helpers import MockRequest

        return MockRequest(user, ip_address)

operator = SwitchManager(auto_create=getattr(settings,
                         'SWITCHBOARD_AUTO_CREATE', True))
