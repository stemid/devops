# Configuration for spamutbildning.py

# People allowed to send commands
ADMINS = [
    'admin@domain.tld',
]

# Working dir must be writable by mail user and/or group
WORKING_DIR = '.'

# Logfile
LOG_FILE = 'spamutbildning.log'
LOG_MAX_BYTES = 20971520 # 20M default
LOG_MAX_COPIES = 5
LOG_FORMAT = '%(asctime)s %(filename)s[%(process)s] %(levelname)s: %(message)s'

# These will be automagically created if they do not exist
TMP_DIR = '{pwd}s/tmp'.format(pwd=WORKING_DIR)
CONFIRMED_DIR = '{pwd}s/confirmed'.format(pwd=WORKING_DIR)

# Go into filenames of queued mail 
TMP_PREFIX = 'tmpmail'
SPAM_PREFIX = 'spam'

# These email formats are counted, the rest is discarded
# because sa-learn does not need to learn binary attachments. 
VALID_FORMATS = [
    'text/plain',
    'text/html',
    'message/rfc822',
]
