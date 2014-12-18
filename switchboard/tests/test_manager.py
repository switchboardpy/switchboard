"""
switchboard.tests.test_manager
~~~~~~~~~~~~~~~

:copyright: (c) 2012 SourceForge.
:license: Apache License 2.0, see LICENSE for more details.
"""

from nose.tools import (
    assert_equals,
    assert_true,
    assert_false,
    assert_raises
)
from mock import patch
from webob import Request
from webob.exc import HTTPNotFound, HTTPFound

from .. import configure
from ..builtins import (
    IPAddressConditionSet,
    HostConditionSet,
    QueryStringConditionSet,
)
from ..decorators import switch_is_active
from ..models import (
    Switch,
    SELECTIVE, DISABLED, GLOBAL, INHERIT,
)
from ..manager import SwitchManager
from ..helpers import MockCollection
from ..settings import settings


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
        Switch.c.drop()

    def test_builtin_registration(self):
        assert_true('switchboard.builtins.QueryStringConditionSet'
                    in self.operator._registry)
        assert_true('switchboard.builtins.IPAddressConditionSet'
                    in self.operator._registry)
        assert_true('switchboard.builtins.HostConditionSet'
                    in self.operator._registry)
        assert_equals(len(list(self.operator.get_condition_sets())), 3,
                      self.operator)

    @patch('switchboard.base.MongoModelDict.get_default')
    def test_error(self, get_default):
        # force the is_active call to fail right away
        get_default.side_effect = Exception('Boom!')
        assert_false(self.operator.is_active('test'))

    def test_exclusions(self):
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

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
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

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
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=DISABLED,
        )
        switch = self.operator['test']

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'
        original_func = self.operator.get_request
        self.operator.get_request = lambda: req

        @switch_is_active('test', operator=self.operator)
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
        self.operator.get_request = original_func

    def test_decorator_with_redirect(self):
        Switch.create(
            key='test',
            status=DISABLED,
        )

        req = Request.blank('/')
        original_func = self.operator.get_request
        self.operator.get_request = lambda: req

        @switch_is_active('test', redirect_to='/foo')
        def test():
            return True

        assert_raises(HTTPFound, test)
        self.operator.get_request = original_func

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
        switch.save()

        assert_true(self.operator.is_active('test'))
        assert_true(self.operator.is_active('test', req))

    def test_disable(self):
        switch = Switch.create(key='test')

        switch = self.operator['test']

        req = Request.blank('/')

        switch.status = DISABLED
        switch.save()

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
        switch.save()

        assert_false(self.operator.is_active('test'))

    def test_ip_address_internal_ips(self):
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

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
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

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
        req = self.operator.as_request(ip_address='192.168.1.1')
        assert_true(self.operator.is_active('test', req))

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
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

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
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

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
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

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
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

        parent_switch = Switch.create(
            key='test'
        )
        parent_switch = self.operator['test']

        parent_switch.add_condition(
            condition_set=condition_set,
            field_name='percent',
            condition='0-50',
        )

        Switch.create(
            key='test:child',
            status=INHERIT,
        )

        # Test parent with selective status.
        parent_switch.status = SELECTIVE
        parent_switch.save()

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '1.1.1.1'
        assert_true(self.operator.is_active('test:child', req))

        req.environ['REMOTE_ADDR'] = '20.20.20.20'
        assert_false(self.operator.is_active('test:child', req))

        # Test parent with disabled status.
        parent_switch.status = DISABLED
        parent_switch.save()

        req.environ['REMOTE_ADDR'] = '1.1.1.1'
        assert_false(self.operator.is_active('test:child', req))

        req.environ['REMOTE_ADDR'] = '20.20.20.20'
        assert_false(self.operator.is_active('test:child', req))

        # Test parent with global status.
        parent_switch.status = GLOBAL
        parent_switch.save()

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
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

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
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

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
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

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


class TestConfigure(object):
    def setup(self):
        self.config = dict(
            mongo_host='mongodb',
            mongo_port=8080,
            mongo_db='test',
            mongo_collection='test_switches',
            debug=True,
            switch_defaults=dict(a=1),
            auto_create=True,
            internal_ips='127.0.0.1',
            cache_hosts=['127.0.0.1']
        )

    def teardown(self):
        Switch.c = MockCollection()

    def assert_settings(self):
        for k, v in self.config.iteritems():
            assert_equals(getattr(settings, 'SWITCHBOARD_%s' % k.upper()), v)

    @patch('switchboard.manager.Connection')
    def test_unnested(self, Connection):
        configure(self.config)
        self.assert_settings()
        assert_false(isinstance(Switch.c, MockCollection))

    @patch('switchboard.manager.Connection')
    def test_nested(self, Connection):
        cfg = {}
        for k, v in self.config.iteritems():
            cfg['switchboard.%s' % k] = v
        cfg['foo.bar'] = 'baz'
        configure(cfg, nested=True)
        self.assert_settings()
        assert_false(isinstance(Switch.c, MockCollection))

    @patch('switchboard.manager.Connection')
    def test_database_failure(self, Connection):
        Connection.side_effect = Exception('Boom!')
        configure(self.config)
        assert_true(isinstance(Switch.c, MockCollection))
