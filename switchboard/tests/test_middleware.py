"""
switchboard.tests.test_manager
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from unittest.mock import Mock, patch
from webob import Request

from .. import operator
from ..middleware import SwitchboardMiddleware


class TestSwitchboardMiddleware:
    def setup_method(self):
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
        assert 'request' in operator.context
        assert pre_request.called
        assert post_request.called
        assert request_finished.called

    @patch('switchboard.middleware.request_finished.send')
    def test_request_finished(self, send):
        req = Request.blank('/')
        self.middleware.request_finished(req)
        assert send.called
