"""
switchboard.tests.test_base
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from mock import patch
from nose.tools import (
    assert_equals,
    assert_true,
    assert_false,
    assert_raises
)

from ..base import ModelDict
from ..models import Model
import six
from six.moves import range


class MockModel(Model):

    def __init__(self, *args, **kwargs):
        self._attrs = []
        for k, v in six.iteritems(kwargs):
            if not hasattr(self, k):
                self._attrs.append(k)
                setattr(self, k, v)

    def __eq__(self, other):
        for attr in self._attrs:
            if not hasattr(other, attr):
                return False
            if getattr(self, attr) != getattr(other, attr):
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
        for n in range(10):
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

    def test_iter(self):
        mydict = ModelDict(MockModel)
        mydict['1'] = MockModel(key='1', value='foo1')
        mydict['2'] = MockModel(key='2', value='foo2')
        mydict['3'] = MockModel(key='3', value='foo3')
        for key in mydict:
            assert_equals(key, mydict[key].key)

    def test_iterkeys(self):
        mydict = ModelDict(MockModel)
        mydict['1'] = MockModel(key='1', value='foo1')
        mydict['2'] = MockModel(key='2', value='foo2')
        mydict['3'] = MockModel(key='3', value='foo3')
        for key in six.iterkeys(mydict):
            assert_equals(key, mydict[key].key)

    def test_itervalues(self):
        mydict = ModelDict(MockModel)
        mydict['1'] = MockModel(key='1', value='foo1')
        mydict['2'] = MockModel(key='2', value='foo2')
        mydict['3'] = MockModel(key='3', value='foo3')
        models = six.itervalues(mydict)
        for model in models:
            assert_true(isinstance(model, MockModel))

    def test_iteritems(self):
        mydict = ModelDict(MockModel)
        mydict['1'] = MockModel(key='1', value='foo1')
        mydict['2'] = MockModel(key='2', value='foo2')
        mydict['3'] = MockModel(key='3', value='foo3')
        items = six.iteritems(mydict)
        for key, model in items:
            assert_equals(key, mydict[key].key)
            assert_equals(model, mydict[key])

    def test_set_missing_key(self):
        mydict = ModelDict(MockModel)
        mydict['1'] = MockModel(value='foo1')
        mymodel = mydict['1']
        assert_true(hasattr(mymodel, 'key'))
        assert_equals(mymodel.key, '1')

    @patch('switchboard.models.Model.remove')
    def test_dict_delete(self, remove):
        mydict = ModelDict(MockModel)
        mydict['1'] = MockModel(key='1', value='foo1')
        del mydict['1']
        assert_true(remove.called)

    def test_dict_get(self):
        mydict = ModelDict(MockModel)
        mymodel = MockModel(key='1', value='foo1')
        mydict['1'] = mymodel
        assert_equals(mydict.get('1'), mymodel)
        assert_equals(mydict.get('2'), None)

    def test_dict_pop(self):
        mydict = ModelDict(MockModel)
        mymodel = MockModel(key='1', value='foo1')
        mydict['1'] = mymodel
        popped = mydict.pop('1')
        assert_equals(popped, mymodel)
        popped = mydict.pop('1')
        assert_equals(popped, None)

    def test_dict_setdefault_no_existing_value(self):
        mydict = ModelDict(MockModel)
        mymodel = MockModel(key='1', value='foo1')
        mydict.setdefault('1', mymodel)
        assert_equals(mydict['1'], mymodel)

    def test_dict_setdefault_existing_value(self):
        mydict = ModelDict(MockModel)
        mymodel = MockModel(key='1', value='foo1')
        mydict['1'] = mymodel
        mydict.setdefault('1', MockModel(key='1', value='foo2'))
        assert_equals(mydict['1'], mymodel)
