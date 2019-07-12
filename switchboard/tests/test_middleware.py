"""
switchboard.tests.test_manager
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from mock import Mock, patch
from nose.tools import assert_true
from webob import Request

from .. import operator
from ..middleware import SwitchboardMiddleware


class TestSwitchboardMiddleware(object):
    def setup(self):
        self.app = Mock()
        self.middleware = SwitchboardMiddleware(self.app)

    @patch('switchboard.middleware.SwitchboardMiddleware.request_finished')
    @patch('switchboard.middleware.SwitchboardMiddleware.post_request')
    @patch('switchboard.middleware.SwitchboardMiddleware.pre_request')
    @patch('switchboard.middleware.Request.get_response')
    def test_call(self, get_response, pre_request, post_request,
                  request_finished):
        environ = {}
        start_response = Mock()
        self.middleware(environ, start_response)
        assert_true('request' in operator.context)
        assert_true(pre_request.called)
        assert_true(post_request.called)
        assert_true(request_finished.called)

    @patch('switchboard.middleware.request_finished.send')
    def test_request_finished(self, send):
        req = Request.blank('/')
        self.middleware.request_finished(req)
        assert_true(send.called)
