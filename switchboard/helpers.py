"""
switchboard.helpers
~~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

import logging
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone

log = logging.getLogger(__name__)


class MockCollection:
    """
    A quick and dirty implementation of PyMongo's Collection API,
    to allow for easy testing without a DB connection.
    """
    def __init__(self, name=''):
        self._data = []
        self.name = name
        self.database = defaultdict(lambda: MockCollection(), name=self)

    def _matches(self, spec, document):
        for k, v in spec.items():
            if k not in document or document[k] != v:
                return False
        return True

    def find_one(self, spec):
        result = self.find(spec)
        return result[0] if result else None

    def find(self, spec=None, sort=None):
        results = []
        if not spec:
            # Return a copy of the list so that updating the returned list does
            # not automatically update the datastore.
            return deepcopy(self._data)
        for d in self._data:
            if self._matches(spec, d):
                results.append(d)
        return results or None

    def _update_partial(self, old, new):
        for k, v in new.items():
            old[k] = v

    def update_one(self, spec, update, upsert=False):
        current = self.find_one(spec)
        if not current:
            if upsert:
                update = update.get('$set', update)
                spec.update(update)
                return self.insert_one(spec)
        else:
            for k, v in update.items():
                if k == '$set':
                    self._update_partial(current, v)
                else:
                    current[k] = v

        return {
            'err': None,
            'n': 1,
            'ok': 1.0,
            'updatedExisting': True
        }

    def delete_one(self, spec):
        doc = self.find_one(spec)
        if doc:
            self._data.remove(doc)
            return {'err': None, 'n': 1, 'ok': 1.0}

    def insert_one(self, document):
        _id = document.get('_id')
        if not _id:
            _id = str(len(self._data))
            document['_id'] = _id

        self._data.append(document)
        return _id

    def drop(self):
        self._data = []

    def count(self):
        return len(self._data)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)
