"""
switchboard.tests.test_models
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""
import copy
import pickle

from nose.tools import (
    assert_equals,
    assert_true,
    assert_false,
    raises,
)
from mock import Mock, patch

from ..builtins import IPAddressConditionSet
from ..manager import SwitchManager
from ..models import (
    Model,
    Switch,
    INHERIT, GLOBAL, SELECTIVE, DISABLED,
    INCLUDE, EXCLUDE,
    _key
)
from ..settings import settings


default_datastore = Model.ds


def reset_datastore():
    # If the datastore has changed, a drop method call may fail. We still
    # want to restore the default datastore.
    try:
        Model.drop()
    except:
        pass
    finally:
        Model.ds = default_datastore


class TestModel(object):
    def teardown(self):
        reset_datastore()

    def test_save_with_key(self):
        key = 'test'
        instance = Model(key=key, foo='bar')
        saved_key = instance.save()
        assert_equals(key, saved_key)
        assert_equals(Model.get(key).foo, 'bar')

    def test_save_without_key(self):
        initial = Model(foo='bar')
        key = initial.save()
        assert_true(hasattr(initial, 'key'))
        assert_equals(key, initial.key)
        assert_equals(Model.get(key).foo, 'bar')

    def test_save_updated(self):
        instance = Model(foo='bar')
        key = instance.save()
        assert_equals(Model.get(key).foo, 'bar')
        instance.foo = 'baz'
        instance.save()
        assert_equals(Model.get(key).foo, 'baz')

    @patch('switchboard.models.Model.post_save.send')
    @patch('switchboard.models.Model.pre_save.send')
    def test_save_signals_new(self, pre_save, post_save):
        instance = Model(foo='bar')
        instance.save()
        pre_save.assert_called_with(None)
        assert_true(post_save.called)

    @patch('switchboard.models.Model.post_save.send')
    @patch('switchboard.models.Model.pre_save.send')
    def test_save_signals_update(self, pre_save, post_save):
        key = 'test'
        Model.create(key=key, foo='bar')
        # Create copies so our in-memory datastore isn't being updated
        # until we actually save.
        instance = copy.deepcopy(Model.get(key))
        # And make a second copy so that previous isn't changed when we update
        # instance.
        previous = copy.deepcopy(instance)
        instance.foo = 'baz'
        instance.save()
        actual_previous = pre_save.call_args[0][0]
        assert_equals(previous.foo, actual_previous.foo)
        assert_true(post_save.called)

    def test_delete(self):
        key = 'test'
        instance = Model.create(key=key)
        assert_true(Model.contains(key))
        instance.delete()
        assert_false(Model.contains(key))

    def test_create(self):
        key = 'test'
        assert_false(Model.contains(key))
        Model.create(key=key)
        assert_true(Model.contains(key))

    def test_get(self):
        key = 'test'
        foo = 'bar'
        Model.create(key=key, foo=foo)
        instance = Model.get(key)
        assert_true(isinstance(instance, Model))
        assert_equals(instance.foo, foo)

    def test_contains(self):
        key = 'test'
        Model.create(key=key)
        assert_true(Model.contains(key))
        assert_false(Model.contains('scooby'))

    @patch('switchboard.models.Model.update')
    def test_get_or_create_get(self, update):
        Model.create(key='0', foo='bar')
        defaults = dict(foo='bar')
        instance, created = Model.get_or_create('0', defaults=defaults)
        assert_false(created)
        assert_false(update.called)
        assert_equals(instance.foo, 'bar')

    @patch('switchboard.models.Model.update')
    @patch('switchboard.models.Model.get')
    def test_get_or_create_create(self, get, update):
        get.return_value = None
        update.return_value = Model(foo='bar', key='0')
        defaults = dict(foo='bar')
        instance, created = Model.get_or_create('0', defaults=defaults)
        assert_true(created)
        assert_true(update.called)
        assert_equals(instance.foo, 'bar')

    def test_update_existing(self):
        key = 'test'
        Model.create(key=key, foo='bar')
        Model.update({'key': key}, {'foo': 'baz'})
        instance = Model.get(key)
        assert_true(instance.foo, 'baz')

    def test_update_upsert(self):
        key = 'test'
        Model.update({'key': key}, {'foo': 'baz'}, upsert=True)
        instance = Model.get(key)
        assert_true(instance.foo, 'baz')

    def test_update_nonexisting(self):
        key = 'test'
        Model.update({'key': key}, {'foo': 'baz'})
        instance = Model.get(key)
        assert_true(instance is None)

    def test_remove(self):
        key = 'test'
        Model.create(key=key)
        assert_true(Model.contains(key))
        Model.remove(key)
        assert_false(Model.contains(key))

    def test_remove_nonexisting(self):
        key = 'test'
        assert_false(Model.contains(key))
        result = Model.remove(key)
        assert_false(Model.contains(key))
        assert_true(result is None)

    @patch('switchboard.models.Model.post_delete.send')
    @patch('switchboard.models.Model.pre_delete.send')
    def test_remove_signals(self, pre_delete, post_delete):
        key = 'test'
        instance = Model.create(key=key)
        Model.remove(key)
        assert_true(pre_delete.called)
        assert_equals(instance.key, pre_delete.call_args[0][0].key)
        assert_true(post_delete.called)
        assert_equals(instance.key, post_delete.call_args[0][0].key)

    def test_all(self):
        assert_equals(len(Model.all()), 0)
        Model.create(key='0')
        assert_equals(len(Model.all()), 1)
        Model.create(key='1')
        assert_equals(len(Model.all()), 2)
        Model.create(key='test:child')
        models = Model.all()
        assert_equals(len(models), 3)
        actual_keys = [model.key for model in models]
        expected_keys = ['0', '1', 'test:child']
        for key in expected_keys:
            assert_true(key in actual_keys,
                        '{0} not among returned keys'.format(key))

    def test_queryless_all_redis(self):
        class MockDatastore(object):
            pass
        raw_data = {
            'a': dict(key='a'),
            'b': dict(key='b'),
            'test:child': dict(key='test:child'),
        }
        data = dict()
        for k, v in raw_data.iteritems():
            data[_key(k)] = pickle.dumps(v)
        redis = Mock()
        redis.keys.return_value = data.keys()
        redis.get = lambda k: data[k]
        ds = MockDatastore()
        ds.query = Mock()
        ds.query.side_effect = NotImplementedError
        ds.child_datastore = MockDatastore()
        ds.child_datastore.serializer = pickle
        ds._redis = redis
        ds.get = lambda k: pickle.dumps(redis.get(k))
        Model.ds = ds
        models = Model.all()
        expected_keys = data.keys()
        actual_keys = [_key(model.key) for model in models]
        assert_equals(len(expected_keys), len(actual_keys))
        for key in expected_keys:
            assert_true(key in actual_keys,
                        '{0} not among returned keys'.format(key))

    @raises(NotImplementedError)
    def test_queryless_all_unsupported(self):
        class MockDatastore(object):
            pass
        ds = MockDatastore()
        ds.query = Mock()
        ds.query.side_effect = NotImplementedError
        Model.ds = ds
        Model.all()

    def test_drop(self):
        Model.create(key='0')
        Model.create(key='1')
        Model.create(key='2')
        assert_equals(Model.count(), 3)
        Model.drop()
        assert_equals(Model.count(), 0)

    def test_count(self):
        assert_equals(Model.count(), 0)
        Model.create(key='0')
        assert_equals(Model.count(), 1)
        Model.create(key='1')
        assert_equals(Model.count(), 2)
        Model.remove('1')
        assert_equals(Model.count(), 1)
        Model.remove('0')
        assert_equals(Model.count(), 0)


class TestSwitch(object):
    def setup(self):
        self.condition_set = IPAddressConditionSet()
        self.manager = SwitchManager(auto_create=True)
        self.manager.register(self.condition_set)
        self.switch = Switch(key='test')
        self.switch.value[self.condition_set.get_namespace()] = {
            'ip_address': [
                [INCLUDE, '10.1.1.1'],
                [INCLUDE, '192.168.1.1'],
                [INCLUDE, '127.0.0.1'],
            ],
            'percent': [
                [INCLUDE, '0-50']
            ],
        }

    def teardown(self):
        reset_datastore()

    def test_construct_with_defaults(self):
        settings.SWITCHBOARD_SWITCH_DEFAULTS = {
            'active_by_default': dict(is_active=True, label='active'),
            'inactive_by_default': dict(is_active=False, label='inactive'),
        }
        active_switch = Switch(key='active_by_default')
        assert_equals(active_switch.status, GLOBAL)
        assert_equals(active_switch.label, 'active')
        inactive_switch = Switch(key='inactive_by_default')
        assert_equals(inactive_switch.status, DISABLED)
        assert_equals(inactive_switch.label, 'inactive')

    def test_get_status_display(self):
        assert_equals(Switch(status=INHERIT).get_status_display(),
                      'Inherit')
        assert_equals(Switch(status=GLOBAL).get_status_display(),
                      'Global')
        assert_equals(Switch(status=SELECTIVE).get_status_display(),
                      'Selective')
        assert_equals(Switch(status=DISABLED).get_status_display(),
                      'Disabled')

    @patch('switchboard.models.Switch.save')
    def test_add_condition_include(self, save):
        self.switch.add_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='ip_address',
            condition='10.0.0.2',
        )
        namespace = self.condition_set.get_namespace()
        conditions = self.switch.value[namespace]['ip_address']
        assert_true([INCLUDE, '10.0.0.2'] in conditions)
        assert_true(save.called)

    @patch('switchboard.models.Switch.save')
    def test_add_condition_exclude(self, save):
        self.switch.add_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='ip_address',
            condition='10.0.0.2',
            exclude=True,
        )
        namespace = self.condition_set.get_namespace()
        conditions = self.switch.value[namespace]['ip_address']
        assert_true([EXCLUDE, '10.0.0.2'] in conditions)
        assert_true(save.called)

    @patch('switchboard.models.Switch.save')
    def test_add_condition_no_commit(self, save):
        self.switch.add_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='ip_address',
            condition='10.0.0.2',
            commit=False,
        )
        namespace = self.condition_set.get_namespace()
        conditions = self.switch.value[namespace]['ip_address']
        assert_true([INCLUDE, '10.0.0.2'] in conditions)
        assert_false(save.called)

    @patch('switchboard.models.Switch.save')
    def test_remove_condition_single(self, save):
        '''
        Remove one and only one condition.
        '''
        self.switch.remove_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='ip_address',
            condition='10.1.1.1',
        )
        namespace = self.condition_set.get_namespace()
        assert_equals(self.switch.value[namespace]['ip_address'],
                      [[INCLUDE, '192.168.1.1'],
                       [INCLUDE, '127.0.0.1']])
        assert_true(save.called)

    @patch('switchboard.models.Switch.save')
    def test_remove_condition_multiple(self, save):
        '''
        Remove multiple conditions.

        Should leave the others untouched when deleting a condition, and should
        remove the keys when no more conditions remain.
        '''
        namespace = self.condition_set.get_namespace()
        self.switch.remove_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='ip_address',
            condition='192.168.1.1',
        )
        assert_true(self.condition_set.get_namespace() in self.switch.value)
        assert_true('ip_address' in self.switch.value[namespace])
        assert_equals(self.switch.value[namespace]['ip_address'],
                      [[INCLUDE, '10.1.1.1'],
                       [INCLUDE, '127.0.0.1']])
        assert_equals(save.call_count, 1)
        self.switch.remove_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='ip_address',
            condition='10.1.1.1',
        )
        self.switch.remove_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='ip_address',
            condition='127.0.0.1',
        )
        assert_true(self.condition_set.get_namespace() in self.switch.value)
        assert_false('ip_address' in self.switch.value[namespace])
        assert_equals(self.switch.value[namespace]['percent'],
                      [[INCLUDE, '0-50']])
        assert_equals(save.call_count, 3)
        self.switch.remove_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='percent',
            condition='0-50',
        )
        assert_false(self.condition_set.get_namespace() in self.switch.value)
        assert_equals(save.call_count, 4)

    @patch('switchboard.models.Switch.save')
    def test_remove_condition_no_commit(self, save):
        self.switch.remove_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='ip_address',
            condition='10.1.1.1',
            commit=False
        )
        namespace = self.condition_set.get_namespace()
        assert_equals(self.switch.value[namespace]['ip_address'],
                      [[INCLUDE, '192.168.1.1'],
                       [INCLUDE, '127.0.0.1']])
        assert_false(save.called)

    @patch('switchboard.models.Switch.save')
    def test_remove_condition_not_found(self, save):
        # Test a field name that doesn't exist.
        self.switch.remove_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='foo',
            condition='bar',
        )
        namespace = self.condition_set.get_namespace()
        assert_equals(self.switch.value[namespace]['ip_address'],
                      [[INCLUDE, '10.1.1.1'],
                       [INCLUDE, '192.168.1.1'],
                       [INCLUDE, '127.0.0.1']])
        assert_false(save.called)
        # Test a namespace that doesn't exist.
        MockConditionSet = Mock()
        MockConditionSet.get_namespace = lambda: 'foobar'
        self.manager.get_condition_set_by_id = lambda x: MockConditionSet
        self.switch.remove_condition(
            manager=self.manager,
            condition_set='foobar',  # Due to the mocks, this doesn't matter.
            field_name='foo',
            condition='bar',
        )
        namespace = self.condition_set.get_namespace()
        assert_equals(self.switch.value[namespace]['ip_address'],
                      [[INCLUDE, '10.1.1.1'],
                       [INCLUDE, '192.168.1.1'],
                       [INCLUDE, '127.0.0.1']])
        assert_false(save.called)

    @patch('switchboard.models.Switch.save')
    def test_clear_conditions_with_field_name(self, save):
        self.switch.clear_conditions(self.manager, self.condition_set.get_id(),
                                     field_name='ip_address')
        namespace = self.condition_set.get_namespace()
        assert_false('ip_address' in self.switch.value[namespace])
        assert_equals(self.switch.value[namespace]['percent'],
                      [[INCLUDE, '0-50']])
        assert_true(save.called)

    @patch('switchboard.models.Switch.save')
    def test_clear_conditions_whole_namespace(self, save):
        self.switch.clear_conditions(self.manager, self.condition_set.get_id())
        assert_false(self.condition_set.get_namespace() in self.switch.value)
        assert_true(save.called)

    @patch('switchboard.models.Switch.save')
    def test_clear_conditions_no_commit(self, save):
        set_id = self.condition_set.get_id()
        self.switch.clear_conditions(self.manager, set_id, commit=False)
        assert_false(self.condition_set.get_namespace() in self.switch.value)
        assert_false(save.called)

    def test_get_active_conditions(self):
        conditions = self.switch.get_active_conditions(self.manager)
        # Note that these values are connected to the data created in the
        # switch.value during setup. Both chunks of code should be kept in
        # sync.
        values = [
            '10.1.1.1',
            '192.168.1.1',
            '127.0.0.1',
            '0-50',
        ]
        fields = [
            'ip_address',
            'percent',
        ]
        # field is an object, so direct comparison gets messy.
        for set_id, group, field, value, excluded in conditions:
            assert_equals(set_id, self.condition_set.get_id())
            assert_equals(group, 'IP Address')
            assert_true(value in values)
            assert_true(field.name in fields)

    def test_get_status_label(self):
        self.switch.status = DISABLED
        assert_equals(self.switch.get_status_label(),
                      'Disabled for everyone')
        self.switch.status = GLOBAL
        assert_equals(self.switch.get_status_label(),
                      'Active for everyone')
        self.switch.status = SELECTIVE
        assert_equals(self.switch.get_status_label(),
                      'Active for conditions')
        self.switch.status = INHERIT
        assert_equals(self.switch.get_status_label(),
                      'Inherit from parent')

    def test_get_status_label_selective_no_conditions(self):
        '''
        Tests a selective switch that has no conditions set

        In this case, the switch is essentially globally active.
        '''
        self.switch.status = SELECTIVE
        self.switch.value = None
        assert_equals(self.switch.get_status_label(),
                      'Active for everyone')

    def test_to_dict(self):
        switch_dict = self.switch.to_dict(self.manager)
        assert_equals(switch_dict, {
            'key': 'test',
            'status': DISABLED,
            'status_label': 'Disabled for everyone',
            'label': 'Test',
            'description': '',
            'date_modified': switch_dict['date_modified'],
            'date_created': switch_dict['date_created'],
            'conditions': [
                {
                    'id': self.condition_set.get_id(),
                    'label': 'IP Address',
                    'conditions': [
                        ('ip_address', '10.1.1.1', '10.1.1.1', False),
                        ('ip_address', '192.168.1.1', '192.168.1.1', False),
                        ('ip_address', '127.0.0.1', '127.0.0.1', False),
                        ('percent', '0-50', 'Percent: 50% (0-50)', False),
                    ]
                }
            ]
        })
