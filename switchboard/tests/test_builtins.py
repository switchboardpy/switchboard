"""
switchboard.tests.test_builtins
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

import socket

from nose.tools import assert_true, assert_false
from webob import Request

from ..manager import SwitchManager
from ..builtins import (
    HostConditionSet,
    QueryStringConditionSet,
)
from ..models import Switch, SELECTIVE


def teardown_collection():
    Switch.c.drop()


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
