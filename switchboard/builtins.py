"""
switchboard.builtins
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""
from __future__ import unicode_literals
from __future__ import absolute_import
import socket

from . import operator
from .conditions import (
    RequestConditionSet,
    Percent,
    String,
    Boolean,
    Regex,
    ConditionSet,
    Invalid,
)
from .settings import settings
import six


class IPAddress(String):
    def clean(self, value):
        # Attempt to validate if the proper library is present.
        try:
            import ipaddress
            # The third-party ipaddress lib (not the builtin Python 3 library)
            # requires a unicode string.
            ipaddress.ip_address(six.text_type(value))
        except ImportError:  # pragma: nocover
            pass
        except ValueError:
            raise Invalid
        return value


class IPAddressConditionSet(RequestConditionSet):
    percent = Percent()
    ip_address = IPAddress(label='IP Address')
    internal_ip = Boolean(label='Internal IPs')

    def get_namespace(self):
        return 'ip'

    def get_field_value(self, instance, field_name):
        # XXX: can we come up w/ a better API?
        # Ensure we map ``percent`` to the ``id`` column
        if field_name == 'percent':
            return sum([int(x) for x in instance.remote_addr.split('.')])
        elif field_name == 'ip_address':
            return instance.remote_addr
        elif field_name == 'internal_ip':
            return instance.remote_addr in settings.SWITCHBOARD_INTERNAL_IPS
        return super(IPAddressConditionSet, self).get_field_value(instance,
                                                                  field_name)

    def get_group_label(self):  # pragma: nocover
        return 'IP Address'


operator.register(IPAddressConditionSet())


class QueryStringConditionSet(RequestConditionSet):
    regex = Regex()

    def get_namespace(self):
        return 'querystring'

    def get_field_value(self, instance, field_name):
        return instance.query_string

    def get_group_label(self):
        return 'Query String'


operator.register(QueryStringConditionSet())


class HostConditionSet(ConditionSet):
    hostname = String()

    def get_namespace(self):
        return 'host'

    def can_execute(self, instance):
        return instance is None

    def get_field_value(self, instance, field_name):
        if field_name == 'hostname':
            return socket.gethostname()

    def get_group_label(self):
        return 'Host'


operator.register(HostConditionSet())
