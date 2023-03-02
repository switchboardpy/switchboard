"""
switchboard.builtins
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""
import socket
import ipaddress

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


class IPAddress(String):
    def clean(self, value):
        try:
            ipaddress.ip_address(str(value))
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
            # any number is fine, `Percent` takes it mod 100
            return int(ipaddress.ip_address(instance.remote_addr))
        elif field_name == 'ip_address':
            return instance.remote_addr
        elif field_name == 'internal_ip':
            return instance.remote_addr in settings.SWITCHBOARD_INTERNAL_IPS
        return super().get_field_value(instance, field_name)

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
