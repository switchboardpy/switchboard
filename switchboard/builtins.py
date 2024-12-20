"""
switchboard.builtins
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""
import socket
import ipaddress
import urllib

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

    def _should_include_referrer(self, instance):
        """
        if the request is a POST submit or an AJAX request, then we should include the referrer's query string.
        See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Sec-Fetch-Mode
        """ 
        # early exit
        if not instance.referrer:
            return False
        # form POST
        if (
            instance.method == 'POST'
            and instance.headers.get('Sec-Fetch-Mode', '') == 'navigate'
            and instance.headers.get('Content-Type', '') in ('application/x-www-form-urlencoded',
                                                             'multipart/form-data')
        ):
            return True
        # fetch()
        if instance.headers.get('Sec-Fetch-Mode', '') in ('cors', 'no-cors', 'same-origin'):
            return True
        # xhr request
        if instance.headers.get('X-Requested-With', '') == 'XMLHttpRequest':
            return True

        return False

    def get_namespace(self):
        return 'querystring'

    def get_field_value(self, instance, field_name):
        value = instance.query_string
        if self._should_include_referrer(instance):
            # quick 'n' dirty way to append the referrer's query string
            value = value + '&' + urllib.parse.urlparse(instance.referrer).query
        return value

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
