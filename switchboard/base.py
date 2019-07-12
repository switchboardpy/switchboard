"""
switchboard.base
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
import threading
import six


class ModelDict(threading.local):
    """
    Dictionary-style access to :func:`~switchboard.model.Model` data.

    If ``auto_create=True`` accessing modeldict[key] when key does not exist
    will attempt to create it in the datastore.

    Functions in two different ways, depending on the constructor:

        # Assume the datastore has a record like so:
        # { key: '000-abc', 'name': 'Jim', 'phone': '1235677890' }

        mydict = ModelDict(Model)
        mydict['000-abc']
        >>> Model({ 'key': '000-abc', 'name': 'Jim', 'phone': '1234567890' }) #doctest: +SKIP

    If you want to use another key besides ``key``, you may specify that in the
    constructor:

        mydict = ModelDict(Model, key='phone')
        mydict['1234567890']
        >>> Model({ 'key': '000-abc', 'name': 'Jim', 'phone': '1234567890' }) #doctest: +SKIP

    The ModelDict needs to be thread local so that information is not shared
    across threads, e.g., requests.
    """
    def __init__(self, model, key='key', auto_create=False, *args, **kwargs):
        self._key = key
        self._model = model
        self._auto_create = auto_create

    def __getitem__(self, key):
        if self._auto_create:
            instance = self._model.get_or_create(key)[0]
        else:
            instance = self._model.get(key)
        if instance is None:
            raise KeyError(key)
        return instance

    def __setitem__(self, key, instance):
        if not hasattr(instance, 'key'):
            instance.key = key
        instance.save()

    def __delitem__(self, key):
        self._model.remove(key)

    def __len__(self):  # pragma: nocover
        return self._model.count()

    def __contains__(self, key):  # pragma: nocover
        return self._model.contains(key)

    def __iter__(self):
        return self.iterkeys()

    def __repr__(self):  # pragma: nocover
        return "<%s>" % (self.__class__.__name__)

    def iteritems(self):
        def make_item(model):
            return (getattr(model, self._key), model)
        items = [make_item(model) for model in self._model.all()]
        return iter(items)

    def itervalues(self):
        return iter(self._model.all())

    def iterkeys(self):
        return iter([getattr(model, self._key) for model in self._model.all()])

    def keys(self):  # pragma: nocover
        return list(self.iterkeys())

    def values(self):  # pragma: nocover
        return list(self.itervalues())

    def items(self):  # pragma: nocover
        return list(self.iteritems())

    def get(self, key, default=None):
        try:
            value = self[key]
        except KeyError:
            value = default
        return value

    def pop(self, key, default=None):
        value = self.get(key, default)
        try:
            del self[key]
        except KeyError:
            pass
        return value

    def setdefault(self, key, instance):
        self._model.get_or_create(key, defaults=instance.__dict__)
