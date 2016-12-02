"""
switchboard.tests.test_base
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from nose.tools import (
    assert_equals,
    assert_true,
    assert_false,
    assert_raises
)
from blinker import Signal

from ..base import ModelDict
from ..models import Model
from ..signals import request_finished


class MockModel(Model):

    def __init__(self, *args, **kwargs):
        self._attrs = []
        for k, v in kwargs.iteritems():
            if not hasattr(self, k):
                self._attrs.append(k)
                setattr(self, k, v)

    def __eq__(self, other):
        for a in self._attrs:
            if not hasattr(other, a):
                return False
            if getattr(self, a) != getattr(other, a):
                return False
        return True


class TestModelDict(object):

    def teardown(self):
        MockModel.drop()

    def test_api_create(self):
        base_count = MockModel.count()
        mydict = ModelDict(MockModel)
        mydict['foo'] = MockModel(key='foo', value='bar')
        assert_true(isinstance(mydict['foo'], MockModel))
        assert_true(hasattr(mydict['foo'], 'key'))
        assert_equals(mydict['foo'].value, 'bar')
        assert_equals(MockModel.get(key='foo').value, 'bar')
        assert_equals(MockModel.count(), base_count + 1)

    def test_api_update(self):
        base_count = MockModel.count()
        mydict = ModelDict(MockModel)
        mydict['foo'] = MockModel(key='foo', value='bar')
        old_key = mydict['foo'].key
        mydict['foo'] = MockModel(key='foo', value='bar2')
        assert_true(isinstance(mydict['foo'], MockModel))
        assert_equals(mydict['foo'].key, old_key)
        assert_equals(mydict['foo'].value, 'bar2')
        assert_equals(MockModel.get(key='foo').value, 'bar2')
        assert_equals(MockModel.count(), base_count + 1)

    def test_api_delete(self):
        base_count = MockModel.count()
        mydict = ModelDict(MockModel)
        mydict['foo'] = MockModel(key='foo', value='bar')
        mydict['foo'].delete()
        assert_true('foo' not in mydict)
        assert_equals(MockModel.count(), base_count)

    def test_no_auto_create(self):
        # without auto_create
        mydict = ModelDict(MockModel)
        assert_raises(KeyError, lambda x: x['hello'], mydict)
        assert_equals(MockModel.count(), 0)

    def test_auto_create_no_value(self):
        # with auto_create and no value
        mydict = ModelDict(MockModel, auto_create=True)
        repr(mydict['hello'])
        assert_equals(MockModel.count(), 1)
        assert_false(hasattr(MockModel.get(key='hello'), 'value'), '')

    def test_auto_create(self):
        # with auto_create and value
        mydict = ModelDict(MockModel, auto_create=True)
        mydict['hello'] = MockModel(key='hello', value='foo')
        assert_equals(MockModel.count(), 1)
        assert_equals(MockModel.get(key='hello').value, 'foo')

    def test_save_behavior(self):
        mydict = ModelDict(MockModel, auto_create=True)
        mydict['hello'] = MockModel(key='hello')
        for n in xrange(10):
            key = str(n) + '-model'
            mydict[key] = MockModel(key=key)
        assert_equals(len(mydict), 11)
        assert_equals(MockModel.count(), 11)

        mydict = ModelDict(MockModel, auto_create=True)
        m = MockModel.get(key='hello')
        m.value = 'bar'
        m.save()

        assert_equals(MockModel.count(), 11)
        assert_equals(len(mydict), 11)
        assert_equals(mydict['hello'].value, 'bar')

        mydict = ModelDict(MockModel, key='key', auto_create=True)
        m = MockModel.get(key='hello')
        m.value = 'bar2'
        m.save()

        assert_equals(MockModel.count(), 11)
        assert_equals(len(mydict), 11)
        assert_equals(mydict['hello'].value, 'bar2')
