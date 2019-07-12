"""
switchboard.tests.test_builtins
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
import socket

from nose.tools import (
    assert_equals,
    assert_false,
    assert_true,
    raises
)
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


class TestIPAddress(object):
    def setup(self):
        self.ip = IPAddress()

    def test_clean_valid_ipv4(self):
        assert_equals(self.ip.clean('192.168.0.1'), '192.168.0.1')

    def test_clean_valid_ipv6(self):
        assert_equals(self.ip.clean('2001:db8::'), '2001:db8::')

    @raises(Invalid)
    def test_clean_invalid(self):
        self.ip.clean('foobar')


class TestIPAddressConditionSet(object):
    def setup(self):
        self.cs = 'switchboard.builtins.IPAddressConditionSet'
        self.ip = '192.168.0.1'
        self.operator = SwitchManager(auto_create=True)
        self.operator.register(IPAddressConditionSet())

    def teardown(self):
        teardown_collection()

    def test_ip_address(self):
        switch = Switch.create(
            key='test',
            status=SELECTIVE
        )
        switch = self.operator['test']
        req = Request.blank('', environ=dict(REMOTE_ADDR=self.ip))
        assert_false(self.operator.is_active('test', req))
        switch.add_condition(
            condition_set=self.cs,
            field_name='ip_address',
            condition=self.ip,
        )
        assert_true(self.operator.is_active('test', req))

    def test_percent(self):
        ip = '192.168.0.1'
        switch = Switch.create(
            key='test',
            status=SELECTIVE
        )
        switch = self.operator['test']
        req = Request.blank('', environ=dict(REMOTE_ADDR=self.ip))
        assert_false(self.operator.is_active('test', req))
        switch.add_condition(
            condition_set=self.cs,
            field_name='percent',
            condition='50-100',  # Upper 50%; the test IP falls in that range.
        )
        assert_true(self.operator.is_active('test', req))

    def test_internal_ip(self):
        ip = '192.168.0.1'
        switch = Switch.create(
            key='test',
            status=SELECTIVE
        )
        switch = self.operator['test']
        req = Request.blank('', environ=dict(REMOTE_ADDR=ip))
        settings.SWITCHBOARD_INTERNAL_IPS = [ip]
        assert_false(self.operator.is_active('test', req))
        switch.add_condition(
            condition_set=self.cs,
            field_name='internal_ip',
            condition='',  # SWITCHBOARD_INTERNAL_IPS is used instead.
        )
        assert_true(self.operator.is_active('test', req))


class TestHostConditionSet(object):
    def setup(self):
        self.operator = SwitchManager(auto_create=True)
        self.operator.register(HostConditionSet())

    def teardown(self):
        teardown_collection()

    def test_simple(self):
        condition_set = 'switchboard.builtins.HostConditionSet'
        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']
        assert_false(self.operator.is_active('test'))
        switch.add_condition(
            condition_set=condition_set,
            field_name='hostname',
            condition=socket.gethostname(),
        )
        assert_true(self.operator.is_active('test'))


class TestQueryStringConditionSet(object):
    def setup(self):
        self.operator = SwitchManager(auto_create=True)
        self.operator.register(QueryStringConditionSet())

    def setup_switch(self, req):
        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']
        assert_false(self.operator.is_active('test', req))
        switch.add_condition(
            condition_set='switchboard.builtins.QueryStringConditionSet',
            field_name='regex',
            condition='alpha',
        )
        return switch

    def teardown(self):
        teardown_collection()

    def test_flag_present(self):
        req = Request.blank('/?alpha')
        self.setup_switch(req)
        assert_true(self.operator.is_active('test', req))

    def test_flag_missing(self):
        req = Request.blank('/?beta')
        self.setup_switch(req)
        assert_false(self.operator.is_active('test', req))

    def test_no_querystring(self):
        req = Request.blank('/')
        self.setup_switch(req)
        assert_false(self.operator.is_active('test', req))
