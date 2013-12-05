"""
switchboard.tests.test_models
~~~~~~~~~~~~~~~

:copyright: (c) 2012 SourceForge.
:license: Apache License 2.0, see LICENSE for more details.
"""

from nose.tools import assert_equals, assert_true

from ..manager import SwitchManager
from ..models import VersioningMongoModel, Switch


class TestVersioningMongoModel(object):
    def setup(self):
        self.m = VersioningMongoModel(_id='0')

    def teardown(self):
        VersioningMongoModel._versioned_collection().drop()

    def test_diff_fields_added(self):
        self.m._previous = dict(a=1, b=2)
        self.m.c.find_one = lambda x: dict(a=1, b=2, c=3)
        delta = self.m._diff()
        assert_equals(delta['added'], dict(c=3))

    def test_diff_fields_deleted(self):
        self.m._previous = dict(a=1, b=2)
        self.m.c.find_one = lambda x: dict(a=1)
        delta = self.m._diff()
        assert_equals(delta['deleted'], ['b'])

    def test_diff_fields_changed(self):
        self.m._previous = dict(a=1, b=2)
        self.m.c.find_one = lambda x: dict(a=1, b=3)
        delta = self.m._diff()
        assert_equals(delta['changed'], dict(b=3))

    def test_diff_fields_same(self):
        self.m._previous = dict(a=1, b=2)
        self.m.c.find_one = lambda x: dict(a=1, b=2)
        delta = self.m._diff()
        assert_equals(delta['changed'], dict())
        assert_equals(delta['added'], dict())
        assert_equals(delta['deleted'], [])

    def test_diff_created(self):
        self.m._previous = None
        self.m.c.find_one = lambda x: dict(a=1, b=2)
        delta = self.m._diff()
        assert_equals(delta['changed'], dict())
        assert_equals(delta['added'], dict(a=1, b=2))
        assert_equals(delta['deleted'], [])

    def test_diff_removed(self):
        self.m._previous = dict(a=1, b=2)
        self.m.c.find_one = lambda x: None
        delta = self.m._diff()
        assert_equals(delta['changed'], dict())
        assert_equals(delta['added'], dict())
        assert_equals(delta['deleted'], ['a', 'b'])

    def test_diff_noop(self):
        self.m._previous = None
        self.m.c.find_one = lambda x: None
        delta = self.m._diff()
        assert_equals(delta, None)


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


class TestSwitch(object):
    def setup(self):
        self.switch = Switch.create(key='test')
        # clear out the initial version
        Switch._versioned_collection().drop()

    def teardown(self):
        Switch.c.drop()
        Switch._versioned_collection().drop()

    def test_save_version_changed(self):
        self.switch.key = 'test2'
        self.switch.save()
        _id = self.switch._id
        assert_equals(self.switch.to_bson(),
                      self.switch.c.find_one(dict(_id=_id)))
        version = self.switch._versioned_collection().find_one(dict(_id=_id))
        assert_true(version)
        assert_equals(version['delta']['changed']['key'], 'test2')
