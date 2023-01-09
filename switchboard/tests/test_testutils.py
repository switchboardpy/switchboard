"""
switchboard.tests.test_testutils
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""


from ..models import (
    Switch,
    DISABLED, GLOBAL,
)
from ..manager import SwitchManager
from ..testutils import switches


def teardown_collection():
    Switch.c.drop()


class TestSwitchContextManager:
    def setup_method(self):
        self.operator = SwitchManager(auto_create=True)

    def teardown_method(self):
        teardown_collection()

    def test_as_decorator(self):
        switch = self.operator['test']
        switch.status = DISABLED

        @switches(self.operator, test=True)
        def test():
            return self.operator.is_active('test')

        assert test()
        assert self.operator['test'].status == DISABLED

        switch.status = GLOBAL
        switch.save()

        @switches(self.operator, test=False)
        def test2():
            return self.operator.is_active('test')

        assert not test2()
        assert self.operator['test'].status == GLOBAL

    def test_context_manager(self):
        switch = self.operator['test']
        switch.status = DISABLED

        with switches(self.operator, test=True):
            assert self.operator.is_active('test')

        assert self.operator['test'].status == DISABLED

        switch.status = GLOBAL
        switch.save()

        with switches(self.operator, test=False):
            assert not self.operator.is_active('test')

        assert self.operator['test'].status == GLOBAL
