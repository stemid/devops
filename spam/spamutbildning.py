#!/usr/bin/env python
# See README.md for more info.
# Configuration settings in settings.py
# By Stefan.Midjich@cygate.se 2012

# Import configuration
import settings

import sys
import os
import tempfile
import email
from email.parser import Parser
from email.MIMEText import MIMEText
import smtplib
import logging
from logging import handlers

# Get effective user permissions
PROC_EUID = os.geteuid()
PROC_EGID = os.getegid()

# Setup logging
formatter = logging.Formatter(settings.LOG_FORMAT)
l = logging.getLogger(__name__)
h = handlers.RotatingFileHandler(
    settings.LOG_FILE, 
    maxBytes=settings.LOG_MAX_BYTES, 
    backupCount=settings.LOG_MAX_COPIES
)
h.setFormatter(formatter)
l.addHandler(h)
l.setLevel(logging.INFO)

def main():
    # Initialize our working environment
    if initDir(settings.TMP_DIR, PROC_EUID, PROC_EGID, 0750) is False:
        l.critical('Failed to init working dir: %s' % settings.TMP_DIR)
        return False

    if initDir(settings.CONFIRMED_DIR, PROC_EUID, PROC_EGID, 0750) is False:
        l.critical('Failed to init working dir: %s' % settings.CONFIRMED_DIR)
        return False

    # Read email from stdin
    try:
        email = Parser().parse(sys.stdin)
    except(email.errors.MessageParseError, email.errors.HeaderParseError), e:
        l.critical('Could not parse email: %s' % str(e))
        return False

    l.info('Received email: from[%s], subject[%s]' % (email.get('from'),
                                                      email.get('subject')))

    # First find out if it's a command from an admin, and act on that.
    if (email.get('Subject').startswith('!DELETE ') or
        email.get('Subject').startswith('!CONFIRM ')):
        l.info('Found admin command in subject: %s' % email.get('Subject'))
        # If it has any of these commands in its subject we 
        # process the email with a different function and 
        # only continue if it returns False.
        if adminMail():
            return True
        l.info('Admin command did not pan out, proceeding')

    # If it's not multipart at this point, simply give up.
    # Admins are allowed to send non-multipart commands. 
    if email.is_multipart() is False:
        l.info('Non-multipart, discarding mail from: %s' % email.get('From'))
        return True

    # Snatch list of payloads from incoming mail
    discardedPayloads = []
    payloads = email.get_payload()
    for p in payloads:
        p.content_type = p.get_content_type()
        # Remove any non-matching payloads
        if p.content_type not in settings.VALID_FORMATS:
            discardedPayloads.append(
                payloads.pop(payloads.index(p))
            )

    # Create temporary file for email
    try:
        emailFile = tempfile.mkstemp(
            dir=settings.TMP_DIR, 
            prefix=settings.TMP_PREFIX
        )
        # Extract the random suffix given to us by tempfile
        tmpSuffix = os.path.basename(emailFile[1])[len(settings.TMP_PREFIX):]
        emailFile = os.fdopen(emailFile[0], 'w')
        l.info('Created temporary suffix ID for email: %s' % tmpSuffix)
    except(OSError, IOError), e:
        l.critical('Could not create temporary email file: %s' % str(e))
        return False

    # Write out email to temporary file
    emailFile.write(str(email))
    emailFile.close()

    # Notification message template for admins
    adminMessage = ADMIN_MSG_TEMPLATE.format(
        systemName=settings.SYSTEM_NAME,
        tmpmailID=tmpSuffix,
        attachmentFormats=', '.join(settings.VALID_FORMATS),
        admins=', '.join(ADMINS)
    )

    # Create the MIME message
    newMail = MIMEText(
        unicode(adminMessage, 'UTF-8'), 
        'plain', 
        'UTF-8'
    )
    m['From'] = settings.SYSTEM_FROM,
    m['Reply-to'] = settings.SYSTEM_REPLY_TO,
    m['Subject'] = SYSTEM_SUBJECT.format(spamID=tmpSuffix),
    m['To'] = ','.join(settings.ADMINS)

    try:
        smtp = smtplib.SMTP(settings.SYSTEM_SMTPHOST)
        smtp.sendmail(
            settings.SYSTEM_FROM, 
            settings.ADMINS, 
            m.as_string()
        )
    except(smtplib.SMTPException), e:
        l.critical('SMTP Exception: %s' % str(e))
        return False
    finally:
        l.info('Email sent to admins: %s' % ','.join(settings.ADMINS))
        smtp.quit()

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

    if e is None:
        return False

    # First extract the sender mail address
    m = re.search('<([^\s\t\r\n])>$', e.get('from'))
    senderEmail = m.group(1)

    # Do we have an admin?
    if senderEmail in settings.ADMINS:
        # Extract command from subject
        m = re.search('!(CONFIRM|DELETE)\s+([A-Za-z0-9_]+)', e.get('subject'))
        cmd = m.group(1)
        arg = m.group(2)

    if arg == '':
        return False

    if cmd == 'CONFIRM':
        try:
            os.rename(
                '%s/%s%s' % (
                    settings.TMP_DIR, 
                    settings.TMP_PREFIX,
                    arg
                ), 
                '%s/%s%s' % (
                    settings.CONFIRMED_DIR, 
                    settings.SPAM_PREFIX,
                    arg
                )
            )
        except(OSError), e:
            # Really the only case I want adminMail to stop execution...
            # TODO: Raise an exception?
            l.critical('Could not move mail: %s' % arg)
            return False

    if cmd == 'DELETE':
        try:
            os.remove('%s/%s%s' % (
                settings.TMP_DIR, 
                settings.TMP_PREFIX,
                arg
            ))
        except(OSError), e:
            l.critical('Could not delete mail: %s: %s' % (arg, str(e)))
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
