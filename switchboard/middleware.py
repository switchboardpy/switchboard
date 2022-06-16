"""
switchboard.middleware
~~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from webob import Request
from switchboard.signals import request_finished
from switchboard import operator


class SwitchboardMiddleware:

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        req = resp = None
        try:
            req = Request(environ)
            operator.context['request'] = req
            self.pre_request(req)
            resp = req.get_response(self.app)
            return resp(environ, start_response)
        finally:
            self.post_request(req, resp)
            self.request_finished(req)

    def pre_request(self, req):  # pragma: nocover
        '''
        Extension point to make it easy to do things before Switchboard starts
        processing a request. For example, adding a user to the operator's
        context.
        '''
        pass

    def post_request(self, req, resp):  # pragma: nocover
        '''
        Extension point to make it easy to hook additional functionality onto
        the end of Switchboard' processing of a request.
        '''
        pass

    def request_finished(self, req):
        if req:
            # Notify Switchboard that the request is finished
            request_finished.send(req)
