# Site configuration here
config = {
    'debug': False,
    'nagios_user1': '/usr/lib/nagios/plugins',
    'user_api_keys': (
        '',
    ),
    'notification_commands': [
        'sms',
        'email',
    ],
    'email_from': 'nagios@nagios.local',
    'email_smarthost': 'localhost',
    'sms_command': '',
    'oplog_dbhost': 'localhost',
    'oplog_dbport': 5432,
    'oplog_dbname': '',
    'oplog_dbuser': '',
    'oplog_dbpass': '',
}

from os.path import join, abspath, dirname

# Helpful functions for relative paths
here = lambda *p: join(abspath(dirname(__file__)), *p)
PROJECT_ROOT = here('.') # settings.py is in PROJECT_ROOT already
root = lambda *p: join(abspath(PROJECT_ROOT), *p)

# This is just an exercise in the possibility of having an external 
# configuration file in json for example. 
class Settings:
    def __init__(self, **kw):
        from fnmatch import filter

        self.config = config

        if kw.get('debug', None) in [True, False]:
            self.set_debug(status=kw.get('debug'))
        else:
            self.set_debug(status=config.get('debug', False))

        # Make all paths absolute
        settings = filter(config.keys(), '*_path')
        for setting in settings:
            config[setting] = root(config[setting])

    # Wrapper for web.py debug mode, just for no reason at all
    def set_debug(self, status=None):
        from web import config as webconfig

        if status is True:
            webconfig.debug = True
        elif status is False:
            webconfig.debug = False
        else:
            if webconfig.debug is True:
                webconfig.debug = False
            else:
                webconfig.debug = True
        self.config['debug'] = webconfig.debug

    @property
    def oplog_dbhost(self):
        return config['oplog_dbhost']

    @property
    def oplog_dbname(self):
        return config['oplog_dbname']

    @property
    def oplog_dbhost(self):
        return config['oplog_dbhost']

    @property
    def oplog_dbpass(self):
        return config['oplog_dbpass']
