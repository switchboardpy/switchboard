"""
switchboard.settings
~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
import six
NoValue = object()


class Settings(object):

    _state = {}

    @classmethod
    def init(cls, **kwargs):
        settings = six.iteritems(kwargs)
        settings = [('SWITCHBOARD_%s' % k.upper(), v) for k, v in settings]
        # convert timeouts to ints
        settings = [(k, int(v) if k.endswith('TIMEOUT') else v)
                    for k, v in settings]
        cls._state.update(dict(settings))
        return cls()

    def __getattr__(self, name, default=NoValue):
        value = self._state.get(name, default)
        if value is NoValue:
            raise AttributeError
        return value

    def __delattr__(self, name):
        del self._state[name]

    def __setattr__(self, name, value):
        self._state[name] = value


settings = Settings.init()
