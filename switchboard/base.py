"""
switchboard.base
~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

import time
import logging
import threading

from .models import MongoModel
from .signals import request_finished
from .settings import settings

log = logging.getLogger(__name__)


NoValue = object()


class CachedDict(threading.local):
    def __init__(self, timeout=30):
        """
        Not guaranteed to be called with expected c'tor args of
        all usages (due to usage of threading.local)
        """
        cls_name = type(self).__name__

        self._cache = None
        self._last_updated = None
        self.timeout = timeout
        self.cache = settings.SWITCHBOARD_CACHE
        self.cache_key = cls_name
        self.last_updated_cache_key = f'{cls_name}.last_updated'

    def __getitem__(self, key):
        self._populate()
        try:
            value = self._cache[key]
        except KeyError:
            value = self.get_default(key)
            if value is NoValue:
                raise
        except (TypeError, AttributeError):
            log.exception('Unable to access the local cache')
            value = self.get_default(key)
            if value is NoValue:
                raise KeyError(key)
        return value

    def __len__(self):  # pragma: nocover
        if self._cache is None:
            self._populate()
        return len(self._cache)

    def __contains__(self, key):  # pragma: nocover
        self._populate()
        return key in self._cache

    def __iter__(self):  # pragma: nocover
        self._populate()
        return iter(self._cache)

    def __repr__(self):  # pragma: nocover
        return "<%s>" % (self.__class__.__name__)

    def iteritems(self):  # pragma: nocover
        self._populate()
        return self._cache.items()

    def itervalues(self):  # pragma: nocover
        self._populate()
        return self._cache.values()

    def iterkeys(self):  # pragma: nocover
        self._populate()
        return self._cache.keys()

    def keys(self):  # pragma: nocover
        return list(self.keys())

    def values(self):  # pragma: nocover
        return list(self.values())

    def items(self):  # pragma: nocover
        self._populate()
        return list(self._cache.items())

    def get(self, key, default=None):
        self._populate()
        return self._cache.get(key, default)

    def pop(self, key, default=NoValue):
        value = self.get(key, default)
        try:
            del self[key]
        except KeyError:
            pass
        return value

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value

    def get_default(self, key):  # pragma: nocover
        return NoValue

    def is_local_expired(self):
        """
        Returns ``True`` if the in-memory cache has expired (based on
        the cached last_updated value).
        """
        proc_last_updated = self._last_updated
        if not proc_last_updated:
            return True

        if time.time() > proc_last_updated + self.timeout:
            return True

        return False

    def has_global_changed(self):
        """
        Returns ``True`` if the global cache has changed (based on
        the last_updated_cache_key value).

        A return value of ``None`` signifies that no data was available.
        """
        # First deal with situations that don't have caching enabled.
        if not self.cache:
            return True
        # Now deal with all "cache is present" situations.
        try:
            cache_last_updated = self.cache.get(self.last_updated_cache_key)
        except:  # pragma: nocover
            log.exception('Unable to get cache last updated')
            return None
        if not cache_last_updated:
            return None

        if int(cache_last_updated) > (self._last_updated or 0):
            return True

        return False

    def get_cache_data(self):
        """
        Pulls data from the cache backend.
        """
        return self._get_cache_data()

    def clear_cache(self):
        """
        Clears the in-process cache.
        """
        self._cache = None
        self._last_updated = None

    def _populate(self, reset=False):
        """
        Ensures the cache is populated and still valid.

        The cache is checked when:

        - The local timeout has been reached
        - The local cache is not set

        The cache is invalid when:

        - The global cache has expired (via last_updated_cache_key)
        """
        if reset:
            self._cache = None
        elif not self.cache:
            self._cache = None
        elif self.is_local_expired():
            now = int(time.time())
            # Avoid hitting memcache if we don't have a local cache.
            if self._cache is None:
                global_changed = True
            else:
                global_changed = self.has_global_changed()

            # If the cache is expired globally, or local cache isn't present.
            if global_changed or self._cache is None:
                # The value may or may not exist in the cache.
                try:
                    self._cache = self.cache.get(self.cache_key)
                    assert isinstance(self._cache, dict)
                except:
                    self._cache = None
                    log.exception('Unable to refresh local cache from global')

                # If for some reason last_updated_cache_key was None (but the
                # cache key wasn't) we should force the key to exist to prevent
                # continuous calls.
                try:
                    last_updated = self.cache.get(self.last_updated_cache_key)
                except:  # pragma: nocover
                    last_updated = None
                    log.exception('Unable to get cache last updated')
                if (global_changed is None
                        and self._cache is not None
                        and not last_updated):
                    try:
                        self.cache.set(self.last_updated_cache_key, now)
                    except:  # pragma: nocover
                        log.exception('Unable to set cache last updated')

            self._last_updated = now

        if self._cache is None:
            self._update_cache_data()

        return self._cache

    def _update_cache_data(self):
        self._cache = self.get_cache_data()
        self._last_updated = int(time.time())
        # We only set last_updated_cache_key when we know the cache is current
        # because setting this will force all clients to invalidate their
        # cached data if it's newer
        if self.cache:
            try:
                self.cache.set(self.cache_key, self._cache)
                self.cache.set(self.last_updated_cache_key, self._last_updated)
            except:  # pragma: nocover
                log.exception('Unable to refresh global cache from database')

    def _get_cache_data(self):
        raise NotImplementedError  # pragma: nocover

    def _cleanup(self, *args, **kwargs):
        # We set _last_updated to a false value to ensure we hit the
        # last_updated cache on the next request
        self._last_updated = None


class MongoModelDict(CachedDict):
    """
    Dictionary-style access to documents in a collection. Populates a cache
    and a local in-memory store to avoid multiple hits to the collection.

    Specifying ``instances=True`` will cause the cache to store instances
    rather than simple values.

    If ``auto_create=True`` accessing mongodict[key] when key does not exist
    will attempt to create it in the collection.

    Functions in two different ways, depending on the constructor:

        # Given a document that has a attribute named ``foo`` where the value
        # is "bar":

        mydict = MongoModelDict(Model, value='foo')
        mydict['test']
        >>> 'bar' #doctest: +SKIP

    If you want to use another key besides ``_id``, you may specify that in the
    constructor. However, this will be used as part of the cache key, so it's
    recommended to access it in the same way throughout your code.

        mydict = MongoModelDict(Model, key='foo', value='id')
        mydict['bar']
        >>> 'test' #doctest: +SKIP

    """
    def __init__(self, model, key='pk', value=None,
                 auto_create=False, *args, **kwargs):
        assert value is not None

        super().__init__(*args, **kwargs)

        cls_name = type(self).__name__
        name = model.__name__

        self.key = key
        self.value = value

        self.model = model
        self.auto_create = auto_create

        self.cache_key = f'{cls_name}:{name}:{self.key}'
        self.last_updated_cache_key = '{}.last_updated:{}:{}'.format(cls_name,
                                                                 name,
                                                                 self.key)
        request_finished.connect(self._cleanup)
        MongoModel.post_save.connect(self._post_save)
        MongoModel.post_delete.connect(self._post_delete)

    def __setitem__(self, key, value):
        if isinstance(value, self.model):
            value = getattr(value, self.value)

        instance, created = self.model.get_or_create(
            defaults={self.value: value},
            **{self.key: key}
        )

        # Ensure we're updating the value in the database if it changes
        if getattr(instance, self.value) != value:
            setattr(instance, self.value, value)
            self.model.update({self.key: key}, {'$set': {self.value: value}})

    def __delitem__(self, key):
        self.model.remove(**{self.key: key})

    def setdefault(self, key, value):
        if isinstance(value, self.model):
            value = getattr(value, self.value)
        self.model.get_or_create(
            defaults={self.value, value},
            **{self.key: key}
        )

    def get_default(self, key):
        if not self.auto_create:
            return NoValue
        result = self.model.get_or_create(**{self.key: key})[0]
        return result

    def _get_cache_data(self):
        return {getattr(i, self.key): i for i in self.model.all()}

    # Signals
    def _post_save(self, sender, **kwargs):
        self._populate(reset=True)

    def _post_delete(self, sender, **kwargs):
        self._populate(reset=True)
