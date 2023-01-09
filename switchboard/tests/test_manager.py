"""
switchboard.tests.test_manager
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""
import threading

import pytest
from unittest.mock import Mock, patch
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
    INCLUDE, EXCLUDE
)
from ..manager import registry, SwitchManager
from ..helpers import MockCollection
from ..settings import settings


class TestAPI:
    def setup_method(self):
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

    def teardown_method(self):
        Switch.c.drop()

    def test_builtin_registration(self):
        assert 'switchboard.builtins.QueryStringConditionSet' in registry
        assert 'switchboard.builtins.IPAddressConditionSet' in registry
        assert 'switchboard.builtins.HostConditionSet' in registry
        assert len(list(self.operator.get_condition_sets())) == 3, self.operator

    def test_unregister(self):
        self.operator.unregister(QueryStringConditionSet)
        condition_set_id = 'switchboard.builtins.QueryStringConditionSet'
        assert condition_set_id not in registry
        assert len(list(self.operator.get_condition_sets())) == 2, self.operator

    def test_get_all_conditions(self):
        conditions = list(self.operator.get_all_conditions())
        assert len(conditions) == 5
        for set_id, label, field in conditions:
            assert set_id in registry

    @patch('switchboard.base.MongoModelDict.get_default')
    def test_error(self, get_default):
        # force the is_active call to fail right away
        get_default.side_effect = Exception('Boom!')
        assert not self.operator.is_active('test')

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
        assert self.operator.is_active('test', req)

        req.environ['REMOTE_ADDR'] = '10.1.1.1'
        assert not self.operator.is_active('test', req)

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
        assert not self.operator.is_active('test', req)

        req.environ['REMOTE_ADDR'] = '10.1.1.1'
        assert not self.operator.is_active('test', req)

    def test_decorator_for_ip_address(self):
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=DISABLED,
        )
        switch = self.operator['test']

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'
        self.operator.context['request'] = req

        @switch_is_active('test', operator=self.operator)
        def test():
            return True

        pytest.raises(HTTPNotFound, test)

        switch.status = SELECTIVE
        switch.save()

        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        assert test()

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

        pytest.raises(HTTPNotFound, test)

        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        assert test()

        switch.clear_conditions(
            condition_set=condition_set,
            field_name='ip_address',
        )

        switch.add_condition(
            condition_set=condition_set,
            field_name='percent',
            condition='50-100',
        )

        assert test()

        switch.clear_conditions(
            condition_set=condition_set,
        )

        switch.add_condition(
            condition_set=condition_set,
            field_name='percent',
            condition='0-50',
        )

        pytest.raises(HTTPNotFound, test)

    def test_decorator_with_redirect(self):
        Switch.create(
            key='test',
            status=DISABLED,
        )

        req = Request.blank('/')
        self.operator.context['request'] = lambda: req

        @switch_is_active('test', redirect_to='/foo')
        def test():
            return True

        pytest.raises(HTTPFound, test)

    def test_global(self):
        switch = Switch.create(
            key='test',
            status=DISABLED,
        )
        switch = self.operator['test']

        req = Request.blank('/')

        assert not self.operator.is_active('test')
        assert not self.operator.is_active('test', req)

        switch.status = GLOBAL
        switch.save()

        assert self.operator.is_active('test')
        assert self.operator.is_active('test', req)

    def test_disable(self):
        switch = Switch.create(key='test')

        switch = self.operator['test']

        req = Request.blank('/')

        switch.status = DISABLED
        switch.save()

        assert not self.operator.is_active('test')

        assert not self.operator.is_active('test', req)

    def test_deletion(self):
        switch = Switch.create(key='test')

        switch = self.operator['test']

        assert 'test' in self.operator

        switch.delete()

        assert 'test' not in self.operator

    def test_expiration(self):
        switch = Switch.create(key='test')

        switch = self.operator['test']

        switch.status = DISABLED
        switch.save()

        assert not self.operator.is_active('test')

    def test_ip_address_internal_ips(self):
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

        Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'

        assert not self.operator.is_active('test', req)

        switch.add_condition(
            condition_set=condition_set,
            field_name='internal_ip',
            condition='1',
        )

        settings.SWITCHBOARD_INTERNAL_IPS = ['192.168.1.1']

        assert self.operator.is_active('test', req)

        settings.SWITCHBOARD_INTERNAL_IPS = []

        assert not self.operator.is_active('test', req)

    def test_ip_address(self):
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']

        req = Request.blank('/')
        req.environ['REMOTE_ADDR'] = '192.168.1.1'

        assert not self.operator.is_active('test', req)

        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='192.168.1.1',
        )

        assert self.operator.is_active('test', req)

        switch.clear_conditions(
            condition_set=condition_set,
        )
        switch.add_condition(
            condition_set=condition_set,
            field_name='ip_address',
            condition='127.0.0.1',
        )

        assert not self.operator.is_active('test', req)

        switch.clear_conditions(
            condition_set=condition_set,
        )

        assert not self.operator.is_active('test', req)

        switch.add_condition(
            condition_set=condition_set,
            field_name='percent',
            condition='50-100',
        )

        assert self.operator.is_active('test', req)

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

        assert 'label' in result
        assert result['label'] == 'my switch'

        assert 'status' in result
        assert result['status'] == SELECTIVE

        assert 'description' in result
        assert result['description'] == 'foo bar baz'

        assert 'key' in result
        assert result['key'] == 'test'

        assert 'conditions' in result
        assert len(result['conditions']) == 1

        condition = result['conditions'][0]
        assert 'id' in condition
        assert condition['id'] == condition_set
        assert 'label' in condition
        assert condition['label'] == 'IP Address'
        assert 'conditions' in condition
        assert len(condition['conditions']) == 1

        inner_condition = condition['conditions'][0]
        assert len(inner_condition) == 4
        assert inner_condition[0], 'ip_address'
        assert inner_condition[1], '192.168.1.1'
        assert inner_condition[2], '192.168.1.1'
        assert not inner_condition[3]

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
        assert not self.operator.is_active('test', req1)

        req2 = Request.blank('/2')
        req2.environ['REMOTE_ADDR'] = '10.1.1.1'
        settings.SWITCHBOARD_INTERNAL_IPS = ['10.1.1.1']
        switch.add_condition(
            condition_set=condition_set,
            field_name='internal_ip',
            condition='1',
        )
        assert self.operator.is_active('test', req2)
        # No longer is_active for IP as we have other conditions
        assert not self.operator.is_active('test', req1)

        switch.remove_condition(
            condition_set=condition_set,
            field_name='internal_ip',
            condition='1',
        )

        # back to inactive for everyone with no conditions
        assert not self.operator.is_active('test', req1)
        assert not self.operator.is_active('test', req2)

    def test_switch_defaults(self):
        """Test that defaults are pulled from SWITCHBOARD_SWITCH_DEFAULTS.

        Requires SwitchManager to use auto_create.

        """
        assert self.operator.is_active('active_by_default')
        assert not self.operator.is_active('inactive_by_default')
        assert (
            self.operator['inactive_by_default'].label ==
            'Default Inactive')
        assert (
            self.operator['active_by_default'].label ==
            'Default Active')
        active_by_default = self.operator['active_by_default']
        active_by_default.status = DISABLED
        active_by_default.save()
        assert not self.operator.is_active('active_by_default')

    def test_invalid_condition(self):
        condition_set = 'switchboard.builtins.IPAddressConditionSet'

        switch = Switch.create(
            key='test',
            status=SELECTIVE,
        )
        switch = self.operator['test']

        req1 = Request.blank('/1')

        # inactive if selective with no conditions
        assert not self.operator.is_active('test', req1)

        req2 = Request.blank('/2')
        req2.environ['REMOTE_ADDR'] = '10.1.1.1'
        settings.SWITCHBOARD_INTERNAL_IPS = ['10.1.1.1']
        switch.add_condition(
            condition_set=condition_set,
            field_name='foo',
            condition='1',
        )
        assert not self.operator.is_active('test', req2)

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
        assert self.operator.is_active('test:child', req)

        req.environ['REMOTE_ADDR'] = '20.20.20.20'
        assert not self.operator.is_active('test:child', req)

        # Test parent with disabled status.
        parent_switch.status = DISABLED
        parent_switch.save()

        req.environ['REMOTE_ADDR'] = '1.1.1.1'
        assert not self.operator.is_active('test:child', req)

        req.environ['REMOTE_ADDR'] = '20.20.20.20'
        assert not self.operator.is_active('test:child', req)

        # Test parent with global status.
        parent_switch.status = GLOBAL
        parent_switch.save()

        req.environ['REMOTE_ADDR'] = '1.1.1.1'
        assert self.operator.is_active('test:child', req)

        req.environ['REMOTE_ADDR'] = '20.20.20.20'
        assert self.operator.is_active('test:child', req)

    def test_parent_override_child_state(self):
        Switch.create(
            key='test',
            status=DISABLED,
        )

        Switch.create(
            key='test:child',
            status=GLOBAL,
        )

        assert not self.operator.is_active('test:child')

    def test_child_state_is_used(self):
        Switch.create(
            key='test',
            status=GLOBAL,
        )

        Switch.create(
            key='test:child',
            status=DISABLED,
        )

        assert not self.operator.is_active('test:child')

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
        assert self.operator.is_active('test:child', req)

        req.environ['REMOTE_ADDR'] = '10.1.1.1'
        assert not self.operator.is_active('test:child', req)

        assert not self.operator.is_active('test:child')

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
        assert not self.operator.is_active('test:child', req)

        req.environ['REMOTE_ADDR'] = '10.1.1.1'
        assert not self.operator.is_active('test:child', req)

        req.environ['REMOTE_ADDR'] = '127.0.0.1'
        assert not self.operator.is_active('test:child', req)

        assert not self.operator.is_active('test:child')

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
        assert self.operator.is_active('test:child', req)

        req.environ['REMOTE_ADDR'] = '10.1.1.1'
        assert not self.operator.is_active('test:child', req)

        req.environ['REMOTE_ADDR'] = '127.0.0.1'
        assert not self.operator.is_active('test:child', req)

        assert not self.operator.is_active('test:child')

    def test_version_switch_no_user(self):
        switch = Mock()
        switch.save_version = Mock()
        self.operator.context = dict()
        self.operator.version_switch(switch)
        switch.save_version.assert_called_with(username='')

    def test_version_switch_user_dict(self):
        username = 'test'
        switch = Mock()
        switch.save_version = Mock()
        self.operator.context = dict(user=dict(username=username))
        self.operator.version_switch(switch)
        switch.save_version.assert_called_with(username=username)

    def test_version_switch_user_class(self):
        username = 'test'
        switch = Mock()
        switch.save_version = Mock()
        self.operator.context = dict(user=Mock(username=username))
        self.operator.version_switch(switch)
        switch.save_version.assert_called_with(username=username)

    def test_version_switch_user_class_properror(self):
        class OurUser:
            @property
            def username(self):
                raise OSError('whoops')
        switch = Mock()
        switch.save_version = Mock()
        self.operator.context = dict(user=OurUser())
        self.operator.version_switch(switch)
        switch.save_version.assert_called_with(username='')

    def test_version_switch_nonuser_class(self):
        class NonUser:
            pass
        switch = Mock()
        switch.save_version = Mock()
        self.operator.context = dict(user=NonUser())
        self.operator.version_switch(switch)
        switch.save_version.assert_called_with(username='')

    def test_version_switch_nonuser_dict(self):
        switch = Mock()
        switch.save_version = Mock()
        self.operator.context = dict(user=dict())
        self.operator.version_switch(switch)
        switch.save_version.assert_called_with(username='')

    def test_version_switch_save_error(self):
        switch = Mock()
        switch.save_version = Mock()
        switch.save_version.side_effect = Exception('Boom!')
        self.operator.context = dict()
        # Don't need to assert, just need to make sure things don't explode.
        self.operator.version_switch(switch)

    @patch('switchboard.base.MongoModelDict.__getitem__')
    def test_defaults_on_key_error(self, getitem):
        getitem.side_effect = KeyError()
        operator = SwitchManager()
        assert operator.is_active('test', default=True)
        assert not operator.is_active('test', default=False)


class TestConfigure:
    def setup_method(self):
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

    def teardown_method(self):
        Switch.c = MockCollection()

    def assert_settings(self):
        for k, v in self.config.items():
            assert getattr(settings, 'SWITCHBOARD_%s' % k.upper()) == v

    @patch('switchboard.manager.MongoClient')
    def test_unnested(self, MongoClient):
        configure(self.config, allow_no_mongo=True)
        self.assert_settings()
        assert not isinstance(Switch.c, MockCollection)

    @patch('switchboard.manager.MongoClient')
    def test_nested(self, MongoClient):
        cfg = {}
        for k, v in self.config.items():
            cfg['switchboard.%s' % k] = v
        cfg['foo.bar'] = 'baz'
        configure(cfg, nested=True, allow_no_mongo=True)
        self.assert_settings()
        assert not isinstance(Switch.c, MockCollection)

    @patch('switchboard.manager.MongoClient')
    def test_database_failure_permitted(self, MongoClient):
        MongoClient.side_effect = Exception('Boom!')
        configure(self.config, allow_no_mongo=True)
        assert isinstance(Switch.c, MockCollection)

    @patch('switchboard.manager.MongoClient')
    def test_database_failure_fails(self, MongoClient):
        class CustomException(Exception):
            pass
        MongoClient.side_effect = CustomException('Boom!')
        with pytest.raises(CustomException):
            configure(self.config)


class TestManagerConcurrency:

    def setup_method(self):
        self.operator = SwitchManager(auto_create=True)
        self.exc = None

    def test_context_thread_safety(self):
        '''
        Verify that switch contexts are not shared across threads (i.e.,
        between requests).
        '''
        def set_context():
            self.operator.context['foo'] = 'bar'

        def verify_context():
            try:
                assert self.operator.context.get('foo') is None
            except Exception as e:
                self.exc = e

        t1 = threading.Thread(target=set_context)
        t1.start()
        t1.join()
        t2 = threading.Thread(target=verify_context)
        t2.start()
        t2.join()

        if self.exc:
            raise self.exc


class TestManagerResultCaching:

    def setup_method(self):
        self.operator = SwitchManager(auto_create=True)
        self.operator.result_cache = {}

    def test_all(self):
        switch = Switch.create(
            key='test',
            status=GLOBAL,
        )
        # first time
        assert self.operator.is_active('test')
        # still the same 2nd time
        assert self.operator.is_active('test')
        # still the same even if something actually changed
        switch.status = DISABLED
        switch.save()
        assert self.operator.is_active('test')
        # changes after cache is cleared
        self.operator.result_cache = {}
        assert not self.operator.is_active('test')
        # make sure the false value was cached too
        switch.status = GLOBAL
        switch.save()
        assert not self.operator.is_active('test')


class TestManagerResultCacheDecorator:

    def setup_method(self):
        # Gets a pure function, otherwise we get an unbound function that we
        # can't call.
        self.with_result_cache = SwitchManager.__dict__['with_result_cache']

        # a simple "is_active" to wrap
        def is_active_func(self, key, *instances, **kwargs):
            return True

        # wrap it with the decorator
        self.cached_is_active_func = self.with_result_cache(is_active_func)

    def test_decorator_nocache(self):
        operator_self = Mock(result_cache=None)
        result = self.cached_is_active_func(operator_self, 'mykey')
        assert result
        assert operator_self.result_cache is None

    def test_decorator_simple(self):
        operator_self = Mock(result_cache={})
        result = self.cached_is_active_func(operator_self, 'mykey')
        assert result
        assert operator_self.result_cache == {
            (('mykey',), ()): True
        }

    def test_decorator_uses_cache(self):
        # Put False in cache, to ensure only the cache is used, not
        # is_active_func.
        operator_self = Mock(result_cache={
            (('mykey',), ()): False
        })
        result = self.cached_is_active_func(operator_self, 'mykey')
        assert not result
        assert operator_self.result_cache == {
            (('mykey',), ()): False
        }

    def test_decorator_with_params(self):
        operator_self = Mock(result_cache={})
        result = self.cached_is_active_func(operator_self, 'mykey',
                                            'someval', a=1, b=2)
        assert result
        assert operator_self.result_cache == {
            (('mykey', 'someval'),
             (('a', 1), ('b', 2))): True
        }

    def test_decorator_uncachable_params(self):
        operator_self = Mock(result_cache={})
        # A dict isn't hashable, can't be cached.
        result = self.cached_is_active_func(operator_self, 'mykey', {})
        assert result
        assert operator_self.result_cache == {}


class TestManagerConstants:
    def setup_method(self):
        self.operator = SwitchManager()

    def test_disabled(self):
        assert hasattr(self.operator, 'DISABLED')
        assert self.operator.DISABLED == DISABLED

    def test_selective(self):
        assert hasattr(self.operator, 'SELECTIVE')
        assert self.operator.SELECTIVE == SELECTIVE

    def test_global(self):
        assert hasattr(self.operator, 'GLOBAL')
        assert self.operator.GLOBAL == GLOBAL

    def test_include(self):
        assert hasattr(self.operator, 'INCLUDE')
        assert self.operator.INCLUDE == INCLUDE

    def test_exclude(self):
        assert hasattr(self.operator, 'EXCLUDE')
        assert self.operator.EXCLUDE == EXCLUDE
