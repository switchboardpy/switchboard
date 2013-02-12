"""
switchboard.tests.test_helpers
~~~~~~~~~~~~~~~

:copyright: (c) 2012 SourceForge.
:license: Apache License 2.0, see LICENSE for more details.
"""

from nose.tools import assert_equals

from ..helpers import MockRequest
from ..manager import SwitchManager


class TestMockRequest(object):
    def setup(self):
        self.operator = SwitchManager()

    def test_empty_attrs(self):
        req = MockRequest()
        assert_equals(req.remote_addr, None)
        assert_equals(req.user, None)

    def test_ip(self):
        req = MockRequest(ip_address='127.0.0.1')
        assert_equals(req.remote_addr, '127.0.0.1')
        assert_equals(req.user, None)

    def test_as_request(self):
        req = self.operator.as_request(ip_address='127.0.0.1')
        assert_equals(req.remote_addr, '127.0.0.1')
