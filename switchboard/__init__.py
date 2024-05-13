"""
switchboard
~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""
from importlib.metadata import version

from .manager import operator, configure

__all__ = ('operator', 'configure', 'VERSION')

try:
    VERSION = version('switchboard')
except Exception as e:  # pragma: nocover
    VERSION = 'unknown'
