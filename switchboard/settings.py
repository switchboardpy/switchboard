"""
switchboard.settings
~~~~~~~~~~~~~

:copyright: (c) 2012 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

from pylons import config


class Settings(object):

    def __init__(self):
        cfg = config.get('switchboard')
        if not cfg:
            return
        if cfg.get('switch_defaults'):
            self.SWITCHBOARD_SWITCH_DEFAULTS = cfg['switch_defaults']
        if cfg.get('auto_create'):
            self.SWITCHBOARD_AUTO_CREATE = cfg['auto_create']
        if cfg.get('interal_ips'):
            self.SWITCHBOARD_INTERNAL_IPS = cfg['internal_ips']

settings = Settings()
