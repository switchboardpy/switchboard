"""
switchboard
~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

__all__ = ('operator', 'configure', 'VERSION')

try:
    VERSION = __import__('pkg_resources') \
        .get_distribution('switchboard').version
except Exception, e:
    VERSION = 'unknown'

from .manager import operator, configure
