"""
switchboard.decorators
~~~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from functools import wraps

from webob.exc import HTTPNotFound, HTTPFound

from . import operator


def switch_is_active(key, redirect_to=None, operator=operator):
    def _switch_is_active(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if not operator.is_active(key):
                if not redirect_to:
                    raise HTTPNotFound('Switch \'%s\' is not active' % key)
                else:
                    raise HTTPFound(location=redirect_to)
            return func(*args, **kwargs)
        return wrapped
    return _switch_is_active
