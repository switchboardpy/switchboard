"""
switchboard.settings
~~~~~~~~~~~~~

:copyright: (c) 2012 Sourceforge.
:license: Apache License 2.0, see LICENSE for more details.
"""


class Settings(object):

    def __init__(self, mongo_host='localhost', mongo_port=27017,
                 mongo_db='switchboard', mongo_collection='switches',
                 **kwargs):
        self.SWITCHBOARD_MONGO_HOST = mongo_host
        self.SWITCHBOARD_MONGO_PORT = mongo_port
        self.SWITCHBOARD_MONGO_DB = mongo_db
        self.SWITCHBOARD_MONGO_COLLECTION = mongo_collection
        if kwargs.get('debug'):
            self.DEBUG = kwargs['debug']
        if kwargs.get('switch_defaults'):
            self.SWITCHBOARD_SWITCH_DEFAULTS = kwargs['switch_defaults']
        if kwargs.get('auto_create'):
            self.SWITCHBOARD_AUTO_CREATE = kwargs['auto_create']
        if kwargs.get('interal_ips'):
            self.SWITCHBOARD_INTERNAL_IPS = kwargs['internal_ips']
        if kwargs.get('cache_hosts'):
            self.SWITCHBOARD_CACHE_HOSTS = kwargs['cache_hosts']


settings = Settings()
