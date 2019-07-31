"""
switchboard.tests.test_testutils
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from nose.tools import (
    assert_equals,
    assert_true,
    assert_false,
)

from ..models import (
    Switch,
    DISABLED, GLOBAL,
)
from ..manager import SwitchManager
from ..testutils import switches


def teardown_collection():
    Switch.c.drop()


class TestSwitchContextManager(object):
    def setup(self):
        self.operator = SwitchManager(auto_create=True)

    def teardown(self):
        teardown_collection()

    def test_as_decorator(self):
        switch = self.operator['test']
        switch.status = DISABLED

        @switches(self.operator, test=True)
        def test():
            return self.operator.is_active('test')

        assert_true(test())
        assert_equals(self.operator['test'].status, DISABLED)

        switch.status = GLOBAL
        switch.save()

        @switches(self.operator, test=False)
        def test2():
            return self.operator.is_active('test')

        assert_false(test2())
        assert_equals(self.operator['test'].status, GLOBAL)

    def test_context_manager(self):
        switch = self.operator['test']
        switch.status = DISABLED

        with switches(self.operator, test=True):
            assert_true(self.operator.is_active('test'))

        assert_equals(self.operator['test'].status, DISABLED)

        switch.status = GLOBAL
        switch.save()

        with switches(self.operator, test=False):
            assert_false(self.operator.is_active('test'))

        assert_equals(self.operator['test'].status, GLOBAL)
