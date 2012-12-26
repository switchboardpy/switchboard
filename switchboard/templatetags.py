"""
switchboard.templatetags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""
from jinja2 import nodes
from jinja2.ext import Extension

from switchboard import operator


class IfSwitchExtension(Extension):
    tags = set(['ifswitch'])

    def __init__(self, environment):
        super(IfSwitchExtension, self).__init__(environment)

    def parse(self, parser):
        lineno = parser.stream.next().lineno
        args = [parser.parse_expression()]
        if parser.stream.skip_if('comma'):
            args.append(parser.parse_expression())
        else:
            args.append(nodes.Const(None))
        body = parser.parse_statements(['name:endifswitch'], drop_needle=True)
        return nodes.CallBlock(self.call_method('_is_active', args),
                [], [], body).set_lineno(lineno)

    def _is_active(self, key, instances, caller):
        if not isinstance(instances, tuple):
            instances = (instances, )
        if operator.is_active(key, *instances):
            return caller()
        else:
            return ''
