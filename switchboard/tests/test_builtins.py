"""
switchboard.tests.test_builtins
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

import socket

import pytest
from webob import Request

from ..manager import SwitchManager
from ..builtins import (
    HostConditionSet,
    IPAddress,
    IPAddressConditionSet,
    QueryStringConditionSet,
)
from ..conditions import Invalid
from ..models import Switch, SELECTIVE
from ..settings import settings


def teardown_collection():
    Switch.c.drop()


class TestIPAddress:
    def setup_method(self):
        self.ip = IPAddress()

    def test_clean_valid_ipv4(self):
        assert self.ip.clean('192.168.0.1') == '192.168.0.1'

    def test_clean_valid_ipv6(self):
        assert self.ip.clean('2001:db8::') == '2001:db8::'

    def test_clean_invalid(self):
        with pytest.raises(Invalid):
            self.ip.clean('foobar')


class TestIPAddressConditionSet:
    def setup_method(self):
        self.cs = 'switchboard.builtins.IPAddressConditionSet'
        self.ip = '192.168.0.1'
        self.ipv6 = '2001:db8:85a3:8d3:1319:8a2e:370:7348'
        self.ipv6alt = '2001:db8:85a3:8d3:1319:8a2e:370:7448'  # different at end, so Percent calculation is different
        self.operator = SwitchManager(auto_create=True)
        self.operator.register(IPAddressConditionSet())

    def teardown_method(self):
        teardown_collection()

    def test_ip_address(self):
        switch = Switch.create(
            key='test',
            status=SELECTIVE
        )
        switch = self.operator['test']
        req = Request.blank('', environ=dict(REMOTE_ADDR=self.ip))
        assert not self.operator.is_active('test', req)
        switch.add_condition(
            condition_set=self.cs,
            field_name='ip_address',
            condition=self.ip,
        )
        assert self.operator.is_active('test', req)

        req_ipv6 = Request.blank('', environ=dict(REMOTE_ADDR=self.ipv6))
        assert not self.operator.is_active('test', req_ipv6)
        switch.add_condition(
            condition_set=self.cs,
            field_name='ip_address',
            condition=self.ipv6,
        )
        assert self.operator.is_active('test', req_ipv6)

    def test_percent(self):
        switch = Switch.create(
            key='test',
            status=SELECTIVE
        )
        switch = self.operator['test']
        req = Request.blank('', environ=dict(REMOTE_ADDR=self.ip))
        assert not self.operator.is_active('test', req)
        switch.add_condition(
            condition_set=self.cs,
            field_name='percent',
            condition='0-50',  # Lower 50%; the test IPs happen to fall in that range.
        )
        assert self.operator.is_active('test', req)

        assert self.operator.is_active('test', Request.blank('', environ=dict(REMOTE_ADDR=self.ipv6)))

        assert not self.operator.is_active('test', Request.blank('', environ=dict(REMOTE_ADDR=self.ipv6alt)))

    def test_internal_ip(self):
        ip = '192.168.0.1'
        switch = Switch.create(
            key='test',
            status=SELECTIVE
        )
        switch = self.operator['test']
        req = Request.blank('', environ=dict(REMOTE_ADDR=ip))
        settings.SWITCHBOARD_INTERNAL_IPS = [ip]
        assert not self.operator.is_active('test', req)
        switch.add_condition(
            condition_set=self.cs,
            field_name='internal_ip',
            condition='',  # SWITCHBOARD_INTERNAL_IPS is used instead.
        )
        assert self.operator.is_active('test', req)


class TestHostConditionSet:
    def setup_method(self):
        self.operator = SwitchManager(auto_create=True)
        self.operator.register(HostConditionSet())

    def teardown_method(self):
        teardown_collection()

    def test_simple(self):
        condition_set = 'switchboard.builtins.HostConditionSet'
        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']
        assert not self.operator.is_active('test')
        switch.add_condition(
            condition_set=condition_set,
            field_name='hostname',
            condition=socket.gethostname(),
        )
        assert self.operator.is_active('test')


class TestQueryStringConditionSet:
    def setup_method(self):
        self.operator = SwitchManager(auto_create=True)
        self.operator.register(QueryStringConditionSet())

    def setup_switch(self, req):
        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']
        assert not self.operator.is_active('test', req)
        switch.add_condition(
            condition_set='switchboard.builtins.QueryStringConditionSet',
            field_name='regex',
            condition='alpha',
        )
        return switch

    def teardown_method(self):
        teardown_collection()

    def test_flag_present(self):
        req = Request.blank('/?alpha')
        self.setup_switch(req)
        assert self.operator.is_active('test', req)

    def test_flag_missing(self):
        req = Request.blank('/?beta')
        self.setup_switch(req)
        assert not self.operator.is_active('test', req)

    def test_no_querystring(self):
        req = Request.blank('/')
        self.setup_switch(req)
        assert not self.operator.is_active('test', req)
