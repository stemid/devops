# Configuration for spamutbildning.py

from os import geteuid, getegid
from os.path import join, abspath, dirname

# Helpful functions for relative paths
here = lambda *x: join(abspath(dirname(__file__)), *x)
WORKING_ROOT = here('.')
root = lambda *x: join(abspath(WORKING_ROOT), *x)

# Name of this mail system
SYSTEM_NAME = 'My system'
SYSTEM_FROM = 'mysystem@system.tld'
SYSTEM_REPLY_TO = 'mysystem@system.tld'
SYSTEM_SUBJECT = 'New spam candidate: {spamID}'
SYSTEM_SMTPHOST = 'localhost'

# People allowed to send commands.
# Also people who receive notifications of new
# mail and, in the future, critical log records. 
# MUST BE ALL LOWER CASE! 
ADMINS = [
    'admin@domain.tld',
]

# Logfile
LOG_DIR = root('logs')
LOG_FILE = '%s/spamutbildning.log' % LOG_DIR # Path must exist
LOG_MAX_BYTES = 20971520 # 20M default
LOG_MAX_COPIES = 5
LOG_FORMAT = '%(asctime)s %(filename)s[%(process)s] %(levelname)s: %(message)s'

# These will be automagically created if they do not exist
TMP_DIR = root('tmp')
SPAM_DIR = root('spam')
HAM_DIR = root('ham')

# Go into filenames of queued mail 
TMP_PREFIX = 'tmpmail'
SPAM_PREFIX = 'spam'
HAM_PREFIX = 'ham'

# These email formats are counted, the rest is discarded
# because sa-learn does not need to learn binary attachments. 
VALID_FORMATS = [
    'text/plain',
    'text/html',
    'message/rfc822',
]

# Template for the notification email sent to admins. 
ADMIN_MSG_TEMPLATE = """Automated message from {systemName}

Received spam candidate with ID {tmpmailID}

Please view attachment for analysis. 

Take action by replying to this message with the following subject:

!SPAM {tmpmailID}
!HAM {tmpmailID}
!DELETE {tmpmailID}

To confirm, or delete, the mail. 

SPAM = Confirm
HAM  = Is not spam
DELETE = Delete

Explanation of the attachments
============

All attachments are original attachments in one of the following
formats:
    {attachmentFormats}

Guide to confirming emails
============

The attached email must be properly formatted, the header must not be HTML 
formatted for example. The header and body must be intact as when they 
arrived to the server. 

It's an admins job to make sure this is so before sending to SpamAssassin
for training. 

This email
============

This email is coming from an automated system and has been sent to the 
following recipients:
    {admins}

If you feel that you should not be receiving this email, contacting one 
of them would be a good idea. 

/ Spamutbildning
"""

PROC_EUID = geteuid()
PROC_EGID = getegid()
