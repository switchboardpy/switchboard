"""
switchboard.helpers
~~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

import logging

from webob import Request

log = logging.getLogger(__name__)


class MockRequest(Request):
    """
    A mock request object which stores a user
    instance and the ip address.
    """
    def __init__(self, user=None, ip_address=None):
        blank = Request.blank('/')
        blank.environ['REMOTE_ADDR'] = ip_address
        super(MockRequest, self).__init__(blank.environ)
        self.user = user
