"""
switchboard.admin.utils
~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
import json
import six

from switchboard.conditions import Invalid
from switchboard.settings import settings


class SwitchboardException(Exception):  # pragma: nocover
    pass


def json_api(func):
    def wrapper(*args, **kwargs):
        "Decorator to make JSON views simpler"
        try:
            response = {
                "success": True,
                "data": func(*args, **kwargs)
            }
        except SwitchboardException as e:
            response = {
                "success": False,
                "data": e.args[0]
            }
        except ValueError:
            response = {
                "success": False,
                "data": "Switch cannot be found"
            }
        except Invalid as e:
            response = {
                "success": False,
                "data": e.args[0],
            }
        except Exception:
            if hasattr(settings, 'DEBUG') and settings.DEBUG:
                import traceback
                traceback.print_exc()
            raise

        # Sanitize any non-JSON-safe fields like datetime or ObjectId.
        def handler(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            else:
                return six.text_type(obj)
        santized_response = json.loads(json.dumps(response, default=handler))
        return santized_response
    return wrapper


def valid_sort_orders():
    fields = ['label', 'date_created', 'date_modified']
    return fields + ['-' + f for f in fields]
