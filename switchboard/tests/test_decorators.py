"""
switchboard.tests.test_decorators
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from nose.tools import assert_equals, raises
from webob.exc import HTTPNotFound, HTTPFound

from ..decorators import switch_is_active
from ..testutils import switches


@switches(test=True)
def test_switch_is_active_active():
    @switch_is_active('test')
    def test():
        pass
    test()


@switches(test=False)
@raises(HTTPNotFound)
def test_switch_is_active_inactive():
    @switch_is_active('test')
    def test():
        pass
    test()


@switches(test=False)
def test_switch_is_active_inactive_redirect():
    location = '/'

    @switch_is_active('test', redirect_to=location)
    def test():
        pass

    try:
        test()
        raise AssertionError('HTTPNotFound was not raised.')
    except HTTPFound as e:
        assert_equals(e.location, location)
