"""
switchboard.helpers
~~~~~~~~~~~~~~~~

:copyright: (c) 2012 SourceForge.
:license: Apache License 2.0, see LICENSE for more details.
"""

import logging
from collections import defaultdict
from copy import deepcopy

from webob import Request

log = logging.getLogger(__name__)


class MockRequest(Request):
    """
    A mock request object which stores a user
    instance and the ip address.
    """
    def __init__(self, user=None, ip_address=None):
        blank = Request.blank('/')
        blank.environ['REMOTE_ADDR'] = ip_address
        super(MockRequest, self).__init__(blank.environ)
        self.user = user


class MockCollection(object):
    """
    A quick and dirty implementation of PyMongo's Collection API,
    to allow for easy testing without a DB connection.
    """
    def __init__(self, name=''):
        self._data = []
        self.name = name
        self.database = defaultdict(lambda: MockCollection(), name=self)

    def _matches(self, spec, document):
        for k, v in spec.iteritems():
            if not document.get(k) or document[k] != v:
                return False
        return True

    def find_one(self, spec):
        result = self.find(spec)
        return result[0] if result else None

    def find(self, spec=None):
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
        for k, v in new.iteritems():
            old[k] = v

    def update(self, spec, update):
        current = self.find_one(spec)
        if not current:
            return {
                'err': None,
                'n': 1,
                'ok': 1.0,
                'updatedExisting': True
            }
        for k, v in update.iteritems():
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

    def remove(self, spec):
        doc = self.find_one(spec)
        if doc:
            self._data.remove(doc)
            return {'err': None, 'n': 1, 'ok': 1.0}

    def save(self, document):
        if not document.get('_id'):
            _id = str(len(self._data))
            document['_id'] = _id
            self._data.append(document)
        else:
            _id = document['_id']
            self.update({'_id': _id}, document)
        return _id

    def drop(self):
        self._data = []

    def count(self):
        return len(self._data)
