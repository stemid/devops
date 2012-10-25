#!/usr/bin/env python
# Reads an email from stdin
# Meant to run by sendmail smrsh as mail user
# By Stefan.Midjich@cygate.se 2012

# People allowed to send commands
ADMINS = [
    'stefan.midjich@cygate.se',
    'henrik.svensson@cygate.se',
    'driftopsyd@cygate.se',
]

# Working dir must be writable by mail user and/or group
WORKING_DIR = '.'

# Logfile
LOG_FILE = 'spamutbildning.log'

# These will be automagically created if they do not exist
TMP_DIR = '{pwd}s/tmp'.format(pwd=WORKING_DIR)
CONFIRMED_DIR = '{pwd}s/confirmed'.format(pwd=WORKING_DIR)

import sys
import os
import tempfile
import email
from email.parser import Parser
import smtplib
import logging
from logging import handlers

# Get effective user permissions
PROC_EUID = os.geteuid()
PROC_EGID = os.getegid()

# setup logging
logFormat = '%(asctime)s %(filename)s[%(process)s] %(levelname)s: %(message)s'

logging.basicConfig(
    format=logFormat,
    filename=LOG_FILE,
    level=logging.DEBUG,
)
l = logging.getLogger(__name__)

def main():
    if initDir(TMP_DIR, PROC_EUID, PROC_EGID, 0750) is False:
        l.critical('Could not initialize working directory: %s' % TMP_DIR)
        return False

    if initDir(CONFIRMED_DIR, PROC_EUID, PROC_EGID, 0750) is False:
        l.critical('Could not initialize working directory: %s' % CONFIRMED_DIR)
        return False

    # Read email from stdin
    try:
        email = Parser().parse(sys.stdin)
    except(email.errors.MessageParseError, email.errors.HeaderParseError), e:
        l.critical('Could not parse email: %s' % str(e))
        return False

    l.info('Received email: from[%s], subject[%s]' % (email.get('from'),
                                                      email.get('subject')))

    # First find out if it's a command from an admin
    if (email.get('Subject').startswith('!DELETE ') or
        email.get('Subject').startswith('!CONFIRM ')):
        l.info('Found admin command in subject: %s' % email.get('Subject'))
        # If it has any of these two commands in its subject
        # we process the email with a different function and 
        # only continue if it returns False.
        if adminMail():
            return True
        l.info('Admin command did not pan out, proceeding')

    # If it's not multipart at this point, simply give up
    if email.is_multipart() is False:
        l.info('Non-multipart email, discarding mail from: %s' % email.get('From'))
        return True

    # Create temporary file for email
    try:
        emailFile = tempfile.mkstemp(dir=TMP_DIR, prefix='tmpmail')
    except(OSError), e:
        l.critical('Could not create temporary email file')
        return False

    try:
        fp = open(emailFile, 'w')
    except(OSError, IOError), e:
        l.critical('Could not open email file for writing: %s' % emailFile)
        return False

    fp.write(str(email))
    fp.close()

    # Now send out notifications to admins
    adminMessage = ''
    # TODO: Create MIME message and add payload to it
    try:
        smtp = smtplib.SMTP('localhost')
        smtp.sendmail('mail@rsmail020.skane.se', ADMINS, adminMessage)
        smtp.quit()
    except(smtplib.SMTPException), e:
        l.critical('SMTP Exception: %s' % str(e))
        return False

    return True

# Administration function to process command mails
# This returns back to main() even if there is an 
# error condition. Main() is better equipped to handle
# it, and this way execution can proceed in case of
# accidental execution of adminMail().
def adminMail(e=None):
    import re

    cmd = None
    arg = None

    # First extract the sender mail address
    m = re.search('<([^\s\t\r\n])>$', e.get('from'))
    senderEmail = m.group(1)

    # Do we have an admin?
    if senderEmail in ADMINS:
        # Extract command from subject
        m = re.search('!(CONFIRM|DELETE)\s+([A-Za-z0-9_]+)', e.get('subject'))
        cmd = m.group(1)
        arg = m.group(2)

    if cmd == 'CONFIRM':
        try:
            os.rename('%s/tmpmail%s' % (TMP_DIR, arg), 
                      '%s/spam%s' % (CONFIRMED_DIR, arg))
        except(OSError), e:
            # Really the only case I want adminMail to stop execution...
            # TODO: Raise an exception?
            l.critical('Could not move mail: %s' % arg)
            return False

    if cmd == 'DELETE':
        try:
            os.remove('%s/tmpmail%s' % (TMP_DIR, arg))
        except(OSError), e:
            l.critical('Could not delete mail: %s' % arg)
            return False

    # Return false and proceed with execution by default
    return False

def initDir(d=None, dirowner=0, dirgroup=0, dirmode=0000):
    # Check if dir exists first
    try:
        dirStat = os.stat(d)
    except(OSError), e:
        l.info('Directory does not exist or is unreadable: %s' % d)
        # Try creating dir
        try:
            os.mkdir(d, dirmode)
        except(OSError), e:
            l.critical('Could not create directory: %s' % (d, str(e)))
            return False
        finally:
            dirStat = os.stat(d)
    finally:
        # Check its permissions
        if dirStat.st_uid != dirowner or dirStat.st_gid != dirgroup:
            try:
                os.chown(d, dirowner, dirgroup)
            except(OSError), e:
                l.critical('Could not set owner of directory: %s: %s' %
                           (d, str(e)))
                return False
    return True

if __name__ == '__main__':
    if main():
        sys.exit(0)
    sys.exit(1)
