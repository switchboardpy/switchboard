"""
switchboard
~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from .manager import operator, configure

__all__ = ('operator', 'configure', 'VERSION')

try:
    VERSION = __import__('pkg_resources') \
        .get_distribution('switchboard').version
except Exception as e:  # pragma: nocover
    VERSION = 'unknown'
