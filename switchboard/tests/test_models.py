"""
switchboard.tests.test_models
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from datetime import datetime

from unittest.mock import Mock, patch

from ..builtins import IPAddressConditionSet
from ..manager import SwitchManager
from ..models import (
    MongoModel,
    VersioningMongoModel,
    Switch,
    INHERIT, GLOBAL, SELECTIVE, DISABLED,
    INCLUDE, EXCLUDE,
)
from ..settings import settings


class TestMongoModel:
    def setup_method(self):
        self.m = MongoModel()

    def teardown_method(self):
        MongoModel.c.drop()

    @patch('switchboard.models.MongoModel.update')
    def test_get_or_create_get(self, update):
        self.m.create(key=0, foo='bar')
        defaults = dict(foo='bar')
        instance, created = self.m.get_or_create(defaults=defaults, key=0)
        assert not created
        assert not update.called
        assert instance.foo == 'bar'

    @patch('switchboard.models.MongoModel.update')
    @patch('switchboard.helpers.MockCollection.find_one')
    def test_get_or_create_create(self, find_one, update):
        find_one.side_effect = [None, dict(foo='bar', key=0)]
        defaults = dict(foo='bar')
        instance, created = self.m.get_or_create(defaults=defaults, key=0)
        assert created
        assert update.called
        assert instance.foo == 'bar'


class TestVersioningMongoModel:
    def setup_method(self):
        self.m = VersioningMongoModel(_id='0')

    def teardown_method(self):
        VersioningMongoModel._versioned_collection().drop()

    def test_diff_fields_added(self):
        self.m.previous_version = lambda: VersioningMongoModel(a=1, b=2)
        self.m.c.find_one = lambda x: dict(a=1, b=2, c=3)
        delta = self.m._diff()
        assert delta['added'] == dict(c=3)

    def test_diff_fields_deleted(self):
        self.m.previous_version = lambda: VersioningMongoModel(a=1, b=2)
        self.m.c.find_one = lambda x: dict(a=1)
        delta = self.m._diff()
        assert delta['deleted'] == dict(b=2)

    def test_diff_fields_changed(self):
        self.m.previous_version = lambda: VersioningMongoModel(a=1, b=2)
        self.m.c.find_one = lambda x: dict(a=1, b=3)
        delta = self.m._diff()
        assert delta['changed'] == dict(b=(2, 3))

    def test_diff_fields_same(self):
        self.m.previous_version = lambda: VersioningMongoModel(a=1, b=2)
        self.m.c.find_one = lambda x: dict(a=1, b=2)
        delta = self.m._diff()
        assert delta['changed'] == dict()
        assert delta['added'] == dict()
        assert delta['deleted'] == dict()

    def test_diff_created(self):
        self.m.previous_version = lambda: None
        self.m.c.find_one = lambda x: dict(a=1, b=2)
        delta = self.m._diff()
        assert delta['changed'] == dict()
        assert delta['added'] == dict(a=1, b=2)
        assert delta['deleted'] == dict()

    def test_diff_removed(self):
        self.m.previous_version = lambda: VersioningMongoModel(a=1, b=2)
        self.m.c.find_one = lambda x: None
        delta = self.m._diff()
        assert delta['changed'] == dict()
        assert delta['added'] == dict()
        assert delta['deleted'] == dict(a=1, b=2)

    def test_diff_noop(self):
        self.m.previous_version = lambda: None
        self.m.c.find_one = lambda x: None
        delta = self.m._diff()
        assert delta == dict(added={}, deleted={}, changed={})

    def test_previous_version_new(self):
        c = Mock()
        c.find.return_value = None
        self.m._versioned_collection = lambda: c
        prev = self.m.previous_version()
        assert not hasattr(prev, '_id')

    def test_previous_version_singlediff(self):
        delta = dict(
            added=dict(a=1, b=2)
        )
        c = Mock()
        c.find.return_value = [dict(timestamp=datetime.utcnow(),
                                    delta=delta)]
        self.m._versioned_collection = lambda: c
        prev = self.m.previous_version()
        assert prev.a == 1
        assert prev.b == 2

    def test_previous_version_multidiff(self):
        v1 = dict(
            timestamp=datetime.utcnow(),
            delta=dict(added=dict(a=1, b=2))
        )
        v2 = dict(
            timestamp=datetime.utcnow(),
            delta=dict(changed=dict(b=(2, 3)))
        )
        v3 = dict(
            timestamp=datetime.utcnow(),
            delta=dict(added=dict(c=4))
        )
        v4 = dict(
            timestamp=datetime.utcnow(),
            delta=dict(deleted=dict(a=1))
        )
        c = Mock()
        c.find.return_value = [v1, v2, v3, v4]
        self.m._versioned_collection = lambda: c
        prev = self.m.previous_version()
        assert prev.b == 3
        assert prev.c == 4
        assert not hasattr(prev, 'a')


class TestConstant:
    def setup_method(self):
        self.operator = SwitchManager()

    def test_disabled(self):
        assert hasattr(self.operator, 'DISABLED')
        assert self.operator.DISABLED == 1

    def test_selective(self):
        assert hasattr(self.operator, 'SELECTIVE')
        assert self.operator.SELECTIVE == 2

    def test_global(self):
        assert hasattr(self.operator, 'GLOBAL')
        assert self.operator.GLOBAL == 3

    def test_include(self):
        assert hasattr(self.operator, 'INCLUDE')
        assert self.operator.INCLUDE == 'i'

    def test_exclude(self):
        assert hasattr(self.operator, 'EXCLUDE')
        assert self.operator.EXCLUDE == 'e'


class TestSwitch:
    def setup_method(self):
        self.condition_set = IPAddressConditionSet()
        self.manager = SwitchManager(auto_create=True)
        self.manager.register(self.condition_set)
        self.switch = Switch.create(key='test')
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

    def teardown_method(self):
        Switch.c.drop()
        Switch._versioned_collection().drop()

    def test_save_version_changed(self):
        self.switch.key = 'test2'
        self.switch.save()
        _id = self.switch._id
        assert (self.switch.to_bson() ==
                      self.switch.c.find_one(dict(_id=_id)))
        vc = self.switch._versioned_collection()
        versions = list(vc.find(dict(switch_id=_id)))
        assert versions
        versions.sort(key=lambda x:x['timestamp'])
        version = versions[-1]
        assert version
        assert version['delta']['changed']['key'] == ('test', 'test2')

    def test_construct_with_defaults(self):
        settings.SWITCHBOARD_SWITCH_DEFAULTS = {
            'active_by_default': dict(is_active=True, label='active'),
            'inactive_by_default': dict(is_active=False, label='inactive'),
        }
        active_switch = Switch(key='active_by_default')
        assert active_switch.status == GLOBAL
        assert active_switch.label == 'active'
        inactive_switch = Switch(key='inactive_by_default')
        assert inactive_switch.status == DISABLED
        assert inactive_switch.label == 'inactive'

    def test_get_status_display(self):
        assert (Switch(status=INHERIT).get_status_display() ==
                      'Inherit')
        assert (Switch(status=GLOBAL).get_status_display() ==
                      'Global')
        assert (Switch(status=SELECTIVE).get_status_display() ==
                      'Selective')
        assert (Switch(status=DISABLED).get_status_display() ==
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
        assert [INCLUDE, '10.0.0.2'] in conditions
        assert save.called

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
        assert [EXCLUDE, '10.0.0.2'] in conditions
        assert save.called

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
        assert [INCLUDE, '10.0.0.2'] in conditions
        assert not save.called

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
        assert (self.switch.value[namespace]['ip_address'] ==
                      [[INCLUDE, '192.168.1.1'],
                       [INCLUDE, '127.0.0.1']])
        assert save.called

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
        assert self.condition_set.get_namespace() in self.switch.value
        assert 'ip_address' in self.switch.value[namespace]
        assert (self.switch.value[namespace]['ip_address'] ==
                      [[INCLUDE, '10.1.1.1'],
                       [INCLUDE, '127.0.0.1']])
        assert save.call_count == 1
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
        assert self.condition_set.get_namespace() in self.switch.value
        assert 'ip_address' not in self.switch.value[namespace]
        assert (self.switch.value[namespace]['percent'] ==
                      [[INCLUDE, '0-50']])
        assert save.call_count == 3
        self.switch.remove_condition(
            manager=self.manager,
            condition_set=self.condition_set.get_id(),
            field_name='percent',
            condition='0-50',
        )
        assert self.condition_set.get_namespace() not in self.switch.value
        assert save.call_count == 4

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
        assert (self.switch.value[namespace]['ip_address'] ==
                      [[INCLUDE, '192.168.1.1'],
                       [INCLUDE, '127.0.0.1']])
        assert not save.called

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
        assert (self.switch.value[namespace]['ip_address'] ==
                      [[INCLUDE, '10.1.1.1'],
                       [INCLUDE, '192.168.1.1'],
                       [INCLUDE, '127.0.0.1']])
        assert not save.called
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
        assert (self.switch.value[namespace]['ip_address'] ==
                      [[INCLUDE, '10.1.1.1'],
                       [INCLUDE, '192.168.1.1'],
                       [INCLUDE, '127.0.0.1']])
        assert not save.called

    @patch('switchboard.models.Switch.save')
    def test_clear_conditions_with_field_name(self, save):
        self.switch.clear_conditions(self.manager, self.condition_set.get_id(),
                                     field_name='ip_address')
        namespace = self.condition_set.get_namespace()
        assert 'ip_address' not in self.switch.value[namespace]
        assert (self.switch.value[namespace]['percent'] ==
                      [[INCLUDE, '0-50']])
        assert save.called

    @patch('switchboard.models.Switch.save')
    def test_clear_conditions_whole_namespace(self, save):
        self.switch.clear_conditions(self.manager, self.condition_set.get_id())
        assert self.condition_set.get_namespace() not in self.switch.value
        assert save.called

    @patch('switchboard.models.Switch.save')
    def test_clear_conditions_no_commit(self, save):
        set_id = self.condition_set.get_id()
        self.switch.clear_conditions(self.manager, set_id, commit=False)
        assert self.condition_set.get_namespace() not in self.switch.value
        assert not save.called

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
            assert set_id == self.condition_set.get_id()
            assert group == 'IP Address'
            assert value in values
            assert field.name in fields

    def test_get_status_label(self):
        self.switch.status = DISABLED
        assert (self.switch.get_status_label() ==
                      'Disabled for everyone')
        self.switch.status = GLOBAL
        assert (self.switch.get_status_label() ==
                      'Active for everyone')
        self.switch.status = SELECTIVE
        assert (self.switch.get_status_label() ==
                      'Active for conditions')
        self.switch.status = INHERIT
        assert (self.switch.get_status_label() ==
                      'Inherit from parent')

    def test_get_status_label_selective_no_conditions(self):
        '''
        Tests a selective switch that has no conditions set

        In this case, the switch is essentially globally active.
        '''
        self.switch.status = SELECTIVE
        self.switch.value = None
        assert (self.switch.get_status_label() ==
                      'Active for everyone')

    def test_to_dict(self):
        switch_dict = self.switch.to_dict(self.manager)
        for cond in switch_dict['conditions']:
            cond['conditions'].sort()
        assert switch_dict == {
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
                        ('ip_address', '127.0.0.1', '127.0.0.1', False),
                        ('ip_address', '192.168.1.1', '192.168.1.1', False),
                        ('percent', '0-50', 'Percent: 50% (0-50)', False),
                    ]
                }
            ]
        }
