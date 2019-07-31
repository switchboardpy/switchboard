"""
switchboard.tests.admin.test_utils
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from datetime import datetime

from mock import patch
from nose.tools import assert_equals, assert_true, raises

from switchboard.admin.utils import (
    SwitchboardException,
    json_api,
    valid_sort_orders,
)
from switchboard.conditions import Invalid
from switchboard.settings import settings


def test_json_api_success():
    data = dict(foo='bar')

    @json_api
    def tester():
        return data

    assert_equals(tester(), dict(success=True, data=data))


def test_json_api_switchboard_exception():
    @json_api
    def tester():
        raise SwitchboardException('Boom!')

    assert_equals(tester(), dict(success=False, data='Boom!'))


def test_json_api_value_error():
    @json_api
    def tester():
        raise ValueError

    assert_equals(tester(), dict(success=False, data='Switch cannot be found'))


def test_json_api_invalid():
    @json_api
    def tester():
        raise Invalid('Boom!')

    assert_equals(tester(), dict(success=False, data='Boom!'))


@raises(Exception)
def test_json_api_exception():
    @json_api
    def tester():
        raise Exception('Boom!')

    tester()


@patch('traceback.print_exc')
def test_json_api_exception_debug(print_exc):
    @json_api
    def tester():
        raise Exception('Boom!')

    settings.DEBUG = True
    try:
        tester()
    except Exception:
        assert_true(print_exc.called)
    else:
        raise AssertionError('Exception not raised.')


def test_json_api_datetime():
    now = datetime.utcnow()

    @json_api
    def tester():
        return dict(now=now)

    assert_equals(tester(), dict(
        success=True,
        data=dict(now=now.isoformat())
    ))


def test_json_api_object():
    class MockObject(object):
        def __str__(self):
            return 'foobar'
    foobar = MockObject()

    @json_api
    def tester():
        return dict(foobar=foobar)

    assert_equals(tester(), dict(
        success=True,
        data=dict(foobar='foobar')
    ))


def test_valid_sort_orders():
    assert_equals(valid_sort_orders(), [
        'label',
        'date_created',
        'date_modified',
        '-label',
        '-date_created',
        '-date_modified',
    ])
