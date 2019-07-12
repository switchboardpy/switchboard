"""
switchboard.testutils
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from functools import wraps

from . import operator


class SwitchContextManager(object):
    """
    Allows temporarily enabling or disabling a switch.

    Ideal for testing.

    >>> @switches(my_switch_name=True)
    >>> def foo():
    >>>     print operator.is_active('my_switch_name')

    >>> def foo():
    >>>     with switches(my_switch_name=True):
    >>>         print operator.is_active('my_switch_name')

    You may also optionally pass an instance of ``SwitchManager``
    as the first argument.

    >>> def foo():
    >>>     with switches(operator, my_switch_name=True):
    >>>         print operator.is_active('my_switch_name')
    """
    def __init__(self, operator=operator, **keys):
        self.operator = operator
        self.is_active_func = operator.is_active
        self.keys = keys
        self._state = {}
        self._values = {
            True: operator.GLOBAL,
            False: operator.DISABLED,
        }

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return inner

    def __enter__(self):
        self.patch()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unpatch()

    def patch(self):
        def is_active(operator):
            is_active_func = operator.is_active

            def wrapped(key, *args, **kwargs):
                if key in self.keys:
                    return self.keys[key]
                return is_active_func(key, *args, **kwargs)
            return wrapped

        self.operator.is_active = is_active(self.operator)

    def unpatch(self):
        self.operator.is_active = self.is_active_func


switches = SwitchContextManager
