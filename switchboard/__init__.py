"""
switchboard
~~~~~~

:copyright: (c) 2012 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)

__all__ = ('operator', 'VERSION')

try:
    VERSION = __import__('pkg_resources') \
        .get_distribution('switchboard').version
except Exception, e:
    VERSION = 'unknown'

from switchboard.manager import operator
