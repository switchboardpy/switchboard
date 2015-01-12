"""
switchboard.manager
~~~~~~~~~~~~~~~~

:copyright: (c) 2012 SourceForge.
:license: Apache License 2.0, see LICENSE for more details.
"""

import logging

from pymongo import Connection

from . import signals
from .base import MongoModelDict
from .models import (
    MongoModel,
    Switch,
    DISABLED, SELECTIVE, GLOBAL, INHERIT,
    INCLUDE, EXCLUDE,
)
from .proxy import SwitchProxy
from .settings import settings, Settings

log = logging.getLogger(__name__)


def nested_config(config):
    cfg = {}
    token = 'switchboard.'
    for k, v in config.iteritems():
        if k.startswith(token):
            cfg[k.replace(token, '')] = v
    return cfg


def configure(config={}, nested=False):
    """
    Useful for when you need to control Switchboard's setup
    """
    if nested:
        config = nested_config(config)
    # Re-read settings to make sure we have everything
    Settings.init(**config)
    # Establish the connection to Mongo
    mongo_timeout = getattr(settings, 'SWITCHBOARD_MONGO_TIMEOUT', None)
    # The config is in ms to match memcached, but pymongo wants seconds
    mongo_timeout = mongo_timeout // 1000 if mongo_timeout else mongo_timeout
    # Ensure we have an integer for port and not a string
    mongo_port = int(settings.SWITCHBOARD_MONGO_PORT)
    try:
        conn = Connection(settings.SWITCHBOARD_MONGO_HOST,
                          mongo_port,
                          network_timeout=mongo_timeout)
        db = conn[settings.SWITCHBOARD_MONGO_DB]
        collection = db[settings.SWITCHBOARD_MONGO_COLLECTION]
        Switch.c = collection
    except:
        log.exception('Unable to connect to the datastore')
    # Register the builtins
    __import__('switchboard.builtins')


class SwitchManager(MongoModelDict):
    DISABLED = DISABLED
    SELECTIVE = SELECTIVE
    GLOBAL = GLOBAL
    INHERIT = INHERIT

    INCLUDE = INCLUDE
    EXCLUDE = EXCLUDE

    def __init__(self, *args, **kwargs):
        # We'll store available conditions in the registry
        self._registry = {}
        # Inject args and kwargs that are known quantities; the SwitchManager
        # will always deal with the Switch model and so on.
        new_args = [Switch]
        for a in args:
            new_args.append(a)
        kwargs['key'] = 'key'
        kwargs['value'] = 'value'
        MongoModel.post_save.connect(self.version_switch)
        MongoModel.post_delete.connect(self.version_switch)
        super(SwitchManager, self).__init__(*new_args, **kwargs)

    def __unicode__(self):
        return "<%s: %s (%s)>" % (self.__class__.__name__,
                                  getattr(self, 'model', ''),
                                  self._registry.values())

    def __getitem__(self, key):
        """
        Returns a SwitchProxy, rather than a Switch. It allows us to
        easily extend the Switches method and automatically include our
        manager instance.
        """
        return SwitchProxy(self, super(SwitchManager, self).__getitem__(key))

    def is_active(self, key, *instances, **kwargs):
        """
        Returns ``True`` if any of ``instances`` match an active switch.
        Otherwise returns ``False``.

        >>> opersator.is_active('my_feature', request) #doctest: +SKIP
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
            request = self.get_request()
            if request:
                instances.append(request)
            user = self.get_user()
            if user:
                instances.append(user)

            # check each switch to see if it can execute
            return_value = False

            for condition_set in self._registry.itervalues():
                result = condition_set.has_active_condition(conditions,
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
        from .helpers import MockRequest

        return MockRequest(user, ip_address)

    def get_request(self):
        """
        A callback to get the request object should be setup during
        switchboard setup.
        """
        pass

    def get_user(self):
        """
        A callback to get the request object should be setup during
        switchboard setup.
        """
        pass

    def version_switch(self, switch):
        user = self.get_user()
        switch.save_version(username=user.username if user else '')


auto_create = getattr(settings, 'SWITCHBOARD_AUTO_CREATE', True)
operator = SwitchManager(auto_create=auto_create)
