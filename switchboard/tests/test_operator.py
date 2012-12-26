"""
switchboard.tests.tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

import socket

from nose.tools import (
    assert_equals,
    assert_true,
    assert_false,
    assert_raises
)
from webob import Request
from webob.exc import HTTPNotFound, HTTPFound
import ming

from switchboard.settings import settings
from switchboard.builtins import (
    IPAddressConditionSet,
    HostConditionSet,
    QueryStringConditionSet,
)
from switchboard.decorators import switch_is_active
from switchboard.helpers import MockRequest
from switchboard.models import Switch, SELECTIVE, DISABLED, GLOBAL, INHERIT
from switchboard.manager import SwitchManager
from switchboard.testutils import switches

config = {
        'ming.gutenberg.uri': 'mim://test/gutenberg'
}
ming.configure(**config)


def teardown_db():
    switch_collection = Switch.m.session._impl(Switch)
    switch_collection.drop()


class TestAPI(object):
    def setup(self):
        settings.SWITCHBOARD_SWITCH_DEFAULTS = {
            'active_by_default': {
              'is_active': True,
              'label': 'Default Active',
              'description': 'When you want the newness',
            },
            'inactive_by_default': {
              'is_active': False,
              'label': 'Default Inactive',
              'description': 'Controls the funkiness.',
            },
        }
        self.operator = SwitchManager(auto_create=True)
        self.operator.register(QueryStringConditionSet)
        self.operator.register(IPAddressConditionSet)
        self.operator.register(HostConditionSet)

    def teardown(self):
        teardown_db()

    def test_builtin_registration(self):
        assert_true('sf.switchboard.builtins.QueryStringConditionSet'
                    in self.operator._registry)
        assert_true('sf.switchboard.builtins.IPAddressConditionSet'
                    in self.operator._registry)
        assert_true('sf.switchboard.builtins.HostConditionSet'
                    in self.operator._registry)
        assert_equals(len(list(self.operator.get_condition_sets())), 3,
                      self.operator)

    def test_exclusions(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']

        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )
        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='10.1.1.1',
            exclude=True
        )

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'
        assert_true(self.operator.is_active('test', req))

        req.environ['REMOTE_ADDR'] = '10.1.1.1'
        assert_false(self.operator.is_active('test', req))

    def test_only_exclusions(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']

        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
            exclude=True
        )

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'
        assert_false(self.operator.is_active('test', req))

        req.environ['REMOTE_ADDR'] = '10.1.1.1'
        assert_false(self.operator.is_active('test', req))

    def test_decorator_for_ip_address(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=DISABLED,
        )
        switch = self.operator['test']

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'

        @switch_is_active('test', req, operator=self.operator)
        def test():
            return True

        assert_raises(HTTPNotFound, test)

        switch.status = SELECTIVE
        switch.save()

        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        assert_true(test())

        # add in a second condition, so that removing the first one won't kick
        # in the "no conditions returns is_active True for selective switches"
        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.2',
        )

        switch.remove_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        assert_raises(HTTPNotFound, test)

        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        assert_true(test())

        switch.clear_conditions(
            condition_set=condition_set,
            field_name='ip_address',
        )

        switch.add_condition(
            condition_set=condition_set,
            field_name='percent',
            condition='50-100',
        )

        assert_true(test())

        switch.clear_conditions(
            condition_set=condition_set,
        )

        switch.add_condition(
            condition_set=condition_set,
            field_name='percent',
            condition='0-50',
        )

        assert_raises(HTTPNotFound, test)

    def test_decorator_with_redirect(self):
        Switch.create(
            key='test',
            status=DISABLED,
        )

        req = Request.blank('/')

        @switch_is_active('test', req, redirect_to='/foo')
        def test():
            return True

        assert_raises(HTTPFound, test)

    def test_global(self):
        switch = Switch.create(
            key='test',
            status=DISABLED,
        )
        switch = self.operator['test']

        req = Request.blank('/')

        assert_false(self.operator.is_active('test'))
        assert_false(self.operator.is_active('test', req))

        switch.status = GLOBAL
        switch.m.save()

        assert_true(self.operator.is_active('test'))
        assert_true(self.operator.is_active('test', req))

    def test_disable(self):
        switch = Switch.create(key='test')

        switch = self.operator['test']

        req = Request.blank('/')

        switch.status = DISABLED
        switch.m.save()

        assert_false(self.operator.is_active('test'))

        assert_false(self.operator.is_active('test', req))

    def test_deletion(self):
        switch = Switch.create(key='test')

        switch = self.operator['test']

        assert_true('test' in self.operator)

        switch.delete()

        assert_false('test' in self.operator)

    def test_expiration(self):
        switch = Switch.create(key='test')

        switch = self.operator['test']

        switch.status = DISABLED
        switch.m.save()

        assert_false(self.operator.is_active('test'))

    def test_ip_address_internal_ips(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'

        assert_false(self.operator.is_active('test', req))

        switch.add_condition(
            condition_set=condition_set,
            field_name='internal_ip',
            condition='1',
        )

        settings.SWITCHBOARD_INTERNAL_IPS = ['192.168.1.1']

        assert_true(self.operator.is_active('test', req))

        settings.SWITCHBOARD_INTERNAL_IPS = []

        assert_false(self.operator.is_active('test', req))

    def test_ip_address(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'

        assert_false(self.operator.is_active('test', req))

        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        assert_true(self.operator.is_active('test', req))

        switch.clear_conditions(
            condition_set=condition_set,
        )
        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='127.0.0.1',
        )

        assert_false(self.operator.is_active('test', req))

        switch.clear_conditions(
            condition_set=condition_set,
        )

        assert_false(self.operator.is_active('test', req))

        switch.add_condition(
            condition_set=condition_set,
            field_name='percent',
            condition='50-100',
        )

        assert_true(self.operator.is_active('test', req))

        # test with mock request
        assert_true(self.operator.is_active('test',
            self.operator.as_request(ip_address='192.168.1.1')))

        switch.clear_conditions(
            condition_set=condition_set,
        )
        switch.add_condition(
            condition_set=condition_set,
            field_name='percent',
            condition='0-50',
        )
        assert_false(self.operator.is_active('test', req))

    def test_to_dict(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            label='my switch',
            description='foo bar baz',
            key='test',
            status=SELECTIVE,
        )

        switch.add_condition(
            manager=self.operator,
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        result = switch.to_dict(self.operator)

        assert_true('label' in result)
        assert_equals(result['label'], 'my switch')

        assert_true('status' in result)
        assert_equals(result['status'], SELECTIVE)

        assert_true('description' in result)
        assert_equals(result['description'], 'foo bar baz')

        assert_true('key' in result)
        assert_equals(result['key'], 'test')

        assert_true('conditions' in result)
        assert_equals(len(result['conditions']), 1)

        condition = result['conditions'][0]
        assert_true('id' in condition)
        assert_equals(condition['id'], condition_set)
        assert_true('label' in condition)
        assert_equals(condition['label'], 'IP Address')
        assert_true('conditions' in condition)
        assert_equals(len(condition['conditions']), 1)

        inner_condition = condition['conditions'][0]
        assert_equals(len(inner_condition), 4)
        assert_true(inner_condition[0], 'ip_address')
        assert_true(inner_condition[1], '192.168.1.1')
        assert_true(inner_condition[2], '192.168.1.1')
        assert_false(inner_condition[3])

    def test_remove_condition(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']

        req1 = Request.blank('/1')
        req1.environ['REMOTE_ADDR'] = '192.168.1.1'

        # inactive if selective with no conditions
        assert_false(self.operator.is_active('test', req1))

        req2 = Request.blank('/2')
        req2.environ['REMOTE_ADDR'] = '10.1.1.1'
        settings.SWITCHBOARD_INTERNAL_IPS = ['10.1.1.1']
        switch.add_condition(
            condition_set=condition_set,
            field_name='internal_ip',
            condition='1',
        )
        assert_true(self.operator.is_active('test', req2))
        # No longer is_active for IP as we have other conditions
        assert_false(self.operator.is_active('test', req1))

        switch.remove_condition(
            condition_set=condition_set,
            field_name='internal_ip',
            condition='1',
        )

        # back to inactive for everyone with no conditions
        assert_false(self.operator.is_active('test', req1))
        assert_false(self.operator.is_active('test', req2))

    def test_switch_defaults(self):
        """Test that defaults are pulled from SWITCHBOARD_SWITCH_DEFAULTS.

        Requires SwitchManager to use auto_create.

        """
        assert_true(self.operator.is_active('active_by_default'))
        assert_false(self.operator.is_active('inactive_by_default'))
        assert_equals(
            self.operator['inactive_by_default'].label,
            'Default Inactive',
        )
        assert_equals(
            self.operator['active_by_default'].label,
            'Default Active',
        )
        active_by_default = self.operator['active_by_default']
        active_by_default.status = DISABLED
        active_by_default.save()
        assert_false(self.operator.is_active('active_by_default'))

    def test_invalid_condition(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']

        req1 = Request.blank('/1')

        # inactive if selective with no conditions
        assert_false(self.operator.is_active('test', req1))

        req2 = Request.blank('/2')
        req2.environ['REMOTE_ADDR'] = '10.1.1.1'
        settings.SWITCHBOARD_INTERNAL_IPS = ['10.1.1.1']
        switch.add_condition(
            condition_set=condition_set,
            field_name='foo',
            condition='1',
        )
        assert_false(self.operator.is_active('test', req2))

    def test_inheritance(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']

        switch.add_condition(
            condition_set=condition_set,
            field_name='percent',
            condition='0-50',
        )

        switch = Switch.create(
            key='test:child',
            status=INHERIT,
        )
        switch = self.operator['test']

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '1.1.1.1'
        assert_true(self.operator.is_active('test:child', req))

        req.environ['REMOTE_ADDR'] = '20.20.20.20'
        assert_false(self.operator.is_active('test:child', req))

        switch = self.operator['test']
        switch.status = DISABLED

        req.environ['REMOTE_ADDR'] = '1.1.1.1'
        assert_false(self.operator.is_active('test:child', req))

        req.environ['REMOTE_ADDR'] = '20.20.20.20'
        assert_false(self.operator.is_active('test:child', req))

        switch = self.operator['test']
        switch.status = GLOBAL

        req.environ['REMOTE_ADDR'] = '1.1.1.1'
        assert_true(self.operator.is_active('test:child', req))

        req.environ['REMOTE_ADDR'] = '20.20.20.20'
        assert_true(self.operator.is_active('test:child', req))

    def test_parent_override_child_state(self):
        Switch.create(
            key='test',
            status=DISABLED,
        )

        Switch.create(
            key='test:child',
            status=GLOBAL,
        )

        assert_false(self.operator.is_active('test:child'))

    def test_child_state_is_used(self):
        Switch.create(
            key='test',
            status=GLOBAL,
        )

        Switch.create(
            key='test:child',
            status=DISABLED,
        )

        assert_false(self.operator.is_active('test:child'))

    def test_parent_override_child_condition(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        Switch.create(
            key='test',
            status=SELECTIVE,
        )

        parent = self.operator['test']

        parent.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        Switch.create(
            key='test:child',
            status=GLOBAL,
        )

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'
        assert_true(self.operator.is_active('test:child', req))

        req.environ['REMOTE_ADDR'] = '10.1.1.1'
        assert_false(self.operator.is_active('test:child', req))

        assert_false(self.operator.is_active('test:child'))

    def test_child_condition_differing_than_parent_loses(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        Switch.create(
            key='test',
            status=SELECTIVE,
        )

        parent = self.operator['test']

        parent.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        Switch.create(
            key='test:child',
            status=SELECTIVE,
        )

        child = self.operator['test:child']

        child.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='10.1.1.1',
        )

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'
        assert_false(self.operator.is_active('test:child', req))

        req.environ['REMOTE_ADDR'] = '10.1.1.1'
        assert_false(self.operator.is_active('test:child', req))

        req.environ['REMOTE_ADDR'] = '127.0.0.1'
        assert_false(self.operator.is_active('test:child', req))

        assert_false(self.operator.is_active('test:child'))

    def test_child_condition_including_parent_wins(self):
        condition_set = 'sf.switchboard.builtins.IPAddressConditionSet'

        Switch.create(
            key='test',
            status=SELECTIVE,
        )

        parent = self.operator['test']

        parent.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        Switch.create(
            key='test:child',
            status=SELECTIVE,
        )

        child = self.operator['test:child']

        child.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )
        child.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='10.1.1.1',
        )

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'
        assert_true(self.operator.is_active('test:child', req))

        req.environ['REMOTE_ADDR'] = '10.1.1.1'
        assert_false(self.operator.is_active('test:child', req))

        req.environ['REMOTE_ADDR'] = '127.0.0.1'
        assert_false(self.operator.is_active('test:child', req))

        assert_false(self.operator.is_active('test:child'))


class TestConstant(object):
    def setup(self):
        self.operator = SwitchManager()

    def test_disabled(self):
        assert_true(hasattr(self.operator, 'DISABLED'))
        assert_equals(self.operator.DISABLED, 1)

    def test_selective(self):
        assert_true(hasattr(self.operator, 'SELECTIVE'))
        assert_equals(self.operator.SELECTIVE, 2)

    def test_global(self):
        assert_true(hasattr(self.operator, 'GLOBAL'))
        assert_equals(self.operator.GLOBAL, 3)

    def test_include(self):
        assert_true(hasattr(self.operator, 'INCLUDE'))
        assert_equals(self.operator.INCLUDE, 'i')

    def test_exclude(self):
        assert_true(hasattr(self.operator, 'EXCLUDE'))
        assert_equals(self.operator.EXCLUDE, 'e')


class TestMockRequest(object):
    def setup(self):
        self.operator = SwitchManager()

    def test_empty_attrs(self):
        req = MockRequest()
        assert_equals(req.remote_addr, None)
        assert_equals(req.user, None)

    def test_ip(self):
        req = MockRequest(ip_address='127.0.0.1')
        assert_equals(req.remote_addr, '127.0.0.1')
        assert_equals(req.user, None)

    def test_as_request(self):
        req = self.operator.as_request(ip_address='127.0.0.1')
        assert_equals(req.remote_addr, '127.0.0.1')


class TestHostConditionSet(object):
    def setup(self):
        self.operator = SwitchManager(auto_create=True)
        self.operator.register(HostConditionSet())

    def teardown(self):
        teardown_db()

    def test_simple(self):
        condition_set = 'sf.switchboard.builtins.HostConditionSet'

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
            condition_set='sf.switchboard.builtins.QueryStringConditionSet',
            field_name='value',
            condition='alpha',
        )
        return switch

    def teardown(self):
        teardown_db()

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


class TestSwitchContextManager(object):
    def setup(self):
        self.operator = SwitchManager(auto_create=True)

    def teardown(self):
        teardown_db()

    def test_as_decorator(self):
        switch = self.operator['test']
        switch.status = DISABLED

        @switches(self.operator, test=True)
        def test():
            return self.operator.is_active('test')

        assert_true(test())
        assert_equals(self.operator['test'].status, DISABLED)

        switch.status = GLOBAL
        switch.m.save()

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
        switch.m.save()

        with switches(self.operator, test=False):
            assert_false(self.operator.is_active('test'))

        assert_equals(self.operator['test'].status, GLOBAL)
