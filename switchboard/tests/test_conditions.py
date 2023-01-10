"""
switchboard.tests.test_conditions
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

import datetime

from unittest.mock import Mock, patch
import pytest
from webob import Request

from ..conditions import (
    AbstractDate,
    BeforeDate,
    Boolean,
    Choice,
    ConditionSet,
    Field,
    Invalid,
    ModelConditionSet,
    OnOrAfterDate,
    Percent,
    Range,
    Regex,
    RequestConditionSet,
    titlize,
)
from ..models import INCLUDE, EXCLUDE


def test_titlize():
    assert titlize('foo_bar') == 'Foo Bar'
    assert titlize('foobar') == 'Foobar'


class TestField:
    def setup_method(self):
        self.field = Field()

    def test_set_values(self):
        name = 'foo'
        self.field.set_values(name)
        assert self.field.name == name
        assert self.field.label == titlize(name)

    def test_is_active(self):
        assert self.field.is_active('foo', 'foo')
        assert not self.field.is_active('foo', 'bar')

    def test_validate_valid_string(self):
        self.field.name = 'foo'
        assert self.field.validate(dict(foo='bar')) == 'bar'

    def test_validate_invalid_string(self):
        self.field.name = 'foo'
        with pytest.raises(AssertionError):
            self.field.validate(dict(foo=1))

    def test_render(self):
        self.field.name = 'foo'
        assert (self.field.render('bar') ==
                      '<input type="text" value="bar" name="foo"/>')


class TestBoolean:
    def setup_method(self):
        self.field = Boolean()

    def test_is_active(self):
        assert self.field.is_active(None, True)
        assert self.field.is_active(None, 'foo')
        assert not self.field.is_active(None, False)
        assert not self.field.is_active(None, None)

    def test_render(self):
        self.field.name = 'foo'
        assert (self.field.render(None) ==
                      '<input type="hidden" value="1" name="foo"/>')


class TestChoice:
    def setup_method(self):
        choices = ['foo', 'scooby']
        self.field = Choice(choices)

    def test_is_active(self):
        assert self.field.is_active('foo', 'foo')
        assert not self.field.is_active('bar', 'bar')
        assert not self.field.is_active('scooby', 'foo')

    def test_clean_valid_choice(self):
        cleaned = self.field.clean('foo')
        assert isinstance(cleaned, str)
        assert cleaned == 'foo'

    def test_clean_invalid_choice(self):
        with pytest.raises(Invalid):
            self.field.clean('bar')


class TestRange:
    def setup_method(self):
        self.field = Range()
        self.field.name = 'qi'

    def test_is_active(self):
        assert self.field.is_active([0, 50], 25)
        assert self.field.is_active([0, 50], 0)
        assert self.field.is_active([0, 50], 50)
        assert not self.field.is_active([0, 50], -1)
        assert not self.field.is_active([0, 50], 51)

    def test_validate_valid_range(self):
        data = dict()
        data[self.field.name + '[min]'] = '0'
        data[self.field.name + '[max]'] = '50'
        cleaned = self.field.validate(data)
        assert cleaned == '0-50'

    def test_validate_invalid_range(self):
        data = dict()
        data[self.field.name + '[min]'] = 'foo'
        data[self.field.name + '[max]'] = 'bar'
        with pytest.raises(Invalid):
            self.field.validate(data)

    def test_validate_empty_range(self):
        data = dict()
        data[self.field.name + '[min]'] = None
        data[self.field.name + '[max]'] = None
        with pytest.raises(Invalid):
            self.field.validate(data)

    def test_render(self):
        html = (
            '<input type="text" value="0" placeholder="from" name="qi[min]"/>'
            + ' - '
            + '<input type="text" placeholder="to" value="50" name="qi[max]"/>'
        )
        assert self.field.render([0, 50]) == html


class TestPercent:
    def setup_method(self):
        self.field = Percent()
        self.field.label = 'Foo'

    def test_is_active(self):
        assert self.field.is_active('0-50', 25)
        assert self.field.is_active('0-50', 0)
        assert self.field.is_active('0-50', 50)
        assert not self.field.is_active('0-50', -1)
        assert not self.field.is_active('0-50', 51)

    def test_display(self):
        assert self.field.display('0-50') == 'Foo: 50% (0-50)'

    def test_clean_valid_percentile(self):
        assert self.field.clean(['0', '50']) == '0-50'

    def test_clean_percentile_out_of_range(self):
        try:
            self.field.clean(['0', '200'])
            raise AssertionError('Should have thrown an Invalid exception')
        except Invalid as e:
            assert '0 and 100' in e.args[0]

    def test_percentile_min_higher_than_max(self):
        try:
            self.field.clean(['50', '0'])
            raise AssertionError('Should have thrown an Invalid exception')
        except Invalid as e:
            assert 'less than' in e.args[0]


class TestRegex:
    def setup_method(self):
        self.field = Regex()
        self.field.name = 'foo'

    def test_is_active(self):
        assert self.field.is_active('^abc', 'abcdef')
        assert not self.field.is_active('^abc', 'defabc')

    def test_render(self):
        html = ('/<input type="text" value="^abc" name="foo" '
                + 'placeholder="regular expression"/>/')
        assert self.field.render('^abc') == html


class TestAbstractDate:
    def setup_method(self):
        self.field = AbstractDate()

    def test_str_to_date(self):
        date = datetime.date(1900, 1, 1)
        assert self.field.str_to_date('1900-01-01') == date

    def test_display(self):
        self.field.label = 'Foo'
        assert self.field.display('1900-01-01') == 'Foo: 01 Jan 1900'

    def test_clean_valid_date(self):
        assert self.field.clean('1900-01-01') == '1900-01-01'

    def test_clean_invalid_date(self):
        with pytest.raises(Invalid):
            self.field.clean('01-01-1900')

    def test_render_with_date(self):
        self.field.name = 'foo'
        html = '<input type="text" value="1900-01-01" name="foo"/>'
        rendered = self.field.render('1900-01-01')
        assert rendered == html

    def test_render_with_no_date(self):
        self.field.name = 'foo'
        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        html = '<input type="text" value="%s" name="foo"/>' % today_str
        rendered = self.field.render()
        assert rendered == html

    @patch('switchboard.conditions.AbstractDate.date_is_active')
    def test_is_active_with_date(self, date_is_active):
        date_is_active.return_value = True
        date = datetime.date(1900, 1, 1)
        self.field.is_active('1900-01-01', date)
        date_is_active.assert_called_with(date, date)

    @patch('switchboard.conditions.AbstractDate.date_is_active')
    def test_is_active_with_datetime(self, date_is_active):
        date_is_active.return_value = True
        dt = datetime.datetime(1900, 1, 1)
        date = dt.date()
        self.field.is_active('1900-01-01', dt)
        date_is_active.assert_called_with(date, date)

    def test_is_active_with_invalid(self):
        with pytest.raises(AssertionError):
            self.field.is_active('1900-01-01', 'foo')


class TestBeforeDate:
    def setup_method(self):
        self.field = BeforeDate()

    def test_date_is_active(self):
        old_date = datetime.date(1900, 1, 1)
        new_date = datetime.date(2000, 1, 1)
        is_before = self.field.date_is_active
        assert is_before(new_date, old_date)
        assert not is_before(old_date, new_date)
        assert not is_before(new_date, new_date)


class TestOnOrAfterDate:
    def setup_method(self):
        self.field = OnOrAfterDate()

    def test_date_is_active(self):
        old_date = datetime.date(1900, 1, 1)
        new_date = datetime.date(2000, 1, 1)
        on_or_after = self.field.date_is_active
        assert on_or_after(old_date, new_date)
        assert not on_or_after(new_date, old_date)
        assert on_or_after(new_date, new_date)


class TestConditionSet:
    def setup_method(self):
        self.cs = ConditionSet()

    def test_get_field_value_str(self):
        value = 'foo'
        instance = Mock()
        instance.value = value
        assert self.cs.get_field_value(instance, 'value') == value

    def test_get_field_value_percent(self):
        value = 100
        instance = Mock()
        instance.id = value
        assert self.cs.get_field_value(instance, 'percent') == value

    def test_get_field_value_callable(self):
        value = Mock
        instance = Mock()
        instance.value = value
        actual = self.cs.get_field_value(instance, 'value')
        assert isinstance(actual, value)

    @patch('switchboard.conditions.ConditionSet.can_execute')
    @patch('switchboard.conditions.ConditionSet.is_active')
    def test_has_active_conditions_true(self, is_active, can_execute):
        can_execute.side_effect = [True, False]
        is_active.return_value = True
        conditions = {'foo': {'bar': 'baz'}}
        instances = ['foo']
        has_active_condition = self.cs.has_active_condition(conditions,
                                                            instances)
        assert has_active_condition is True
        can_execute.assert_any_call(instances[0])
        is_active.assert_any_call(instances[0], conditions)

    @patch('switchboard.conditions.ConditionSet.can_execute')
    @patch('switchboard.conditions.ConditionSet.is_active')
    def test_has_active_conditions_no_execute(self, is_active, can_execute):
        can_execute.side_effect = [False, False]
        conditions = {'foo': {'bar': 'baz'}}
        instances = ['foo']
        has_active_condition = self.cs.has_active_condition(conditions,
                                                            instances)
        assert has_active_condition is None
        can_execute.assert_any_call(instances[0])
        assert not is_active.called

    @patch('switchboard.conditions.ConditionSet.can_execute')
    @patch('switchboard.conditions.ConditionSet.is_active')
    def test_has_active_conditions_false(self, is_active, can_execute):
        can_execute.side_effect = [True, False]
        is_active.return_value = False
        conditions = {'foo': {'bar': 'baz'}}
        instances = ['foo']
        has_active_condition = self.cs.has_active_condition(conditions,
                                                            instances)
        assert has_active_condition is False
        can_execute.assert_any_call(instances[0])
        is_active.assert_any_call(instances[0], conditions)

    @patch('switchboard.conditions.ConditionSet.get_field_value')
    def test_is_active_include_true(self, get_field_value):
        field = Mock()
        field.is_active.return_value = True
        name = 'bar'
        field_condition = value = 'baz'
        self.cs.fields = {name: field}
        condition = {name: [(INCLUDE, field_condition)]}
        get_field_value.return_value = value
        instance = 'test'
        is_active = self.cs.is_active(instance, condition)
        assert is_active is True
        get_field_value.assert_called_with(instance, name)
        field.is_active.assert_called_with(field_condition, value)

    @patch('switchboard.conditions.ConditionSet.get_field_value')
    def test_is_active_no_field_conditions(self, get_field_value):
        field = Mock()
        field.is_active.return_value = True
        name = 'bar'
        self.cs.fields = {name: field}
        condition = {}
        instance = 'test'
        is_active = self.cs.is_active(instance, condition)
        assert is_active is None
        assert not get_field_value.called
        assert not field.is_active.called

    @patch('switchboard.conditions.ConditionSet.get_field_value')
    def test_is_active_false(self, get_field_value):
        field = Mock()
        field.is_active.return_value = False
        name = 'bar'
        field_condition = value = 'baz'
        self.cs.fields = {name: field}
        condition = {name: [(INCLUDE, field_condition)]}
        get_field_value.return_value = value
        instance = 'test'
        is_active = self.cs.is_active(instance, condition)
        assert is_active is None
        get_field_value.assert_called_with(instance, name)
        field.is_active.assert_called_with(field_condition, value)

    @patch('switchboard.conditions.ConditionSet.get_field_value')
    def test_is_active_true_exclude(self, get_field_value):
        field = Mock()
        field.is_active.return_value = True
        name = 'bar'
        field_condition = value = 'baz'
        self.cs.fields = {name: field}
        condition = {name: [(EXCLUDE, field_condition)]}
        get_field_value.return_value = value
        instance = 'test'
        is_active = self.cs.is_active(instance, condition)
        assert is_active is False
        get_field_value.assert_called_with(instance, name)
        field.is_active.assert_called_with(field_condition, value)


class TestModelConditionSet:
    def setup_method(self):
        class OurModelConditionSet(ModelConditionSet):
            def get_namespace(self):
                return 'ourmodel'

        self.cs = OurModelConditionSet(model=Mock)

    def test_can_execute(self):
        assert self.cs.can_execute(Mock())
        assert not self.cs.can_execute('foo')

    def test_get_id(self):
        assert self.cs.get_id() == 'switchboard.tests.test_conditions.OurModelConditionSet(ourmodel)'

    def test_get_group_label(self):
        assert self.cs.get_group_label() == 'Ourmodel'


class TestRequestConditionSet:
    def setup_method(self):
        self.cs = RequestConditionSet()

    def test_can_execute(self):
        assert self.cs.can_execute(Request.blank('/'))
        assert not self.cs.can_execute('foo')
