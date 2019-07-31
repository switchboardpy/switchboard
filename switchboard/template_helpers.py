"""
switchboard.template_helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from . import operator


def is_active(key, *args):
    """
    Custom test to make checking switches super easy. For example, in
    Jinja:

    {% if 'my_switch' is active %}
    ...
    {% endif %}

    As with the operator.is_active() method, arbitrary objects may be
    passed in for use in testing whether the switch is active:

    {% if 'my_switch' is active(foo) %}
    ...
    {% endif %}

    To setup the test in your jinja environment, update the tests
    dict on the environment:

    from switchboard.template_helpers import is_active
    environment.tests['active'] = is_active
    """
    return operator.is_active(key, *args)
