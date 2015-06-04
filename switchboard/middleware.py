"""
switchboard.middleware
~~~~~~~~~~~~~~~~

:copyright: (c) 2012 SourceForge.
:license: Apache License 2.0, see LICENSE for more details.
"""

from webob import Request
from switchboard.signals import request_finished
from switchboard import operator


class SwitchboardMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        req = resp = None
        try:
            req = Request(environ)
            operator.context['request'] = req
            resp = req.get_response(self.app)
            return resp(environ, start_response)
        finally:
            self._end_request(req)

    def _end_request(self, req):
        if req:
            # Notify Switchboard that the request is finished
            request_finished.send(req)
