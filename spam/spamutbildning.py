#!/usr/bin/env python
# See README.md for more info.
# Configuration settings in settings.py
# By Stefan.Midjich@cygate.se 2012

# Import configuration
import settings

import pdb
import sys
import os
import tempfile
import email
from email.parser import Parser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.generator import Generator
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
l.setLevel(logging.DEBUG)

def main(f=None):
    if f is not None:
        fo = f
    else:
        fo = sys.stdin

    # Initialize our working environment
    if initDir(settings.TMP_DIR, PROC_EUID, PROC_EGID, 0750) is False:
        l.critical('Failed to init working dir: %s' % settings.TMP_DIR)
        return False

    if initDir(settings.CONFIRMED_DIR, PROC_EUID, PROC_EGID, 0750) is False:
        l.critical('Failed to init working dir: %s' % settings.CONFIRMED_DIR)
        return False

    # Read email from stdin
    try:
        inMail = Parser().parse(fo)
    except(email.errors.MessageParseError, email.errors.HeaderParseError), e:
        l.critical('Could not parse email: %s' % str(e))
        return False

    l.info('Received email: from[%s], subject[%s]' % (inMail.get('from'),
                                                      inMail.get('subject')))

    # First find out if it's a command from an admin, and act on that.
    if (inMail.get('Subject').startswith('!DELETE ') or
        inMail.get('Subject').startswith('!CONFIRM ')):
        l.info('Found admin command in subject: %s' % inMail.get('Subject'))
        # If it has any of these commands in its subject we 
        # process the email with a different function and 
        # only continue if it returns False.
        if adminMail(inMail):
            return True
        l.debug('Admin command did not pan out, proceeding')

    # If it's not multipart at this point, simply give up.
    # Admins are allowed to send non-multipart commands. 
    if inMail.is_multipart() is False:
        l.debug('Non-multipart, discarding mail from: %s' % inMail.get('From'))
        return True

    # Create temporary file for incomming email
    try:
        emailFile = tempfile.mkstemp(
            dir=settings.TMP_DIR, 
            prefix=settings.TMP_PREFIX
        )
        # Extract the random suffix given to us by tempfile
        tmpSuffix = os.path.basename(emailFile[1])[len(settings.TMP_PREFIX):]
        emailFile = os.fdopen(emailFile[0], 'w')
    except(OSError, IOError), e:
        l.critical('Could not create temporary email file: %s' % str(e))
        return False
    finally:
        l.debug('Created temporary suffix ID for email: %s' % tmpSuffix)

    # Write out email to temporary file
    emailFile.write(str(inMail))
    emailFile.close()
    l.debug('Wrote temporary email file: %s' % emailFile.name)

    # Create the new mail
    newMail = MIMEMultipart()

    newMail.add_header('From', settings.SYSTEM_FROM)
    newMail.add_header('Reply-to', settings.SYSTEM_REPLY_TO)
    newMail.add_header('Subject',
                       settings.SYSTEM_SUBJECT.format(spamID=tmpSuffix))
    newMail.add_header('To', ','.join(settings.ADMINS))
    newMail.preamble = 'You need a MIME mail reader to read this mail.'

    # Snatch list of payloads from incoming mail
    discardedPayloads = []
    payloads = inMail.get_payload()
    for p in payloads:
        if p.get_content_type() in settings.VALID_FORMATS:
            # Add header to payload and make it an attachment file
            p.add_header(
                'Content-Disposition', 
                'attachment',
                filename='VIRUSKANDIDAT.EML'
            )
            # Attach the payload to main message
            newMail.attach(p)
            l.info('Payload attached to new mail: %s' % p.get_content_type())

    # Notification message template for admins
    adminMessage = settings.ADMIN_MSG_TEMPLATE.format(
        systemName=settings.SYSTEM_NAME,
        tmpmailID=tmpSuffix,
        attachmentFormats=', '.join(settings.VALID_FORMATS),
        admins=', '.join(settings.ADMINS)
    )

    # Add body of message last according to RFC2046
    body = MIMEText(adminMessage, 'plain')
    newMail.attach(body)

    # Send the message
    try:
        smtp = smtplib.SMTP(settings.SYSTEM_SMTPHOST)
        smtp.sendmail(
            settings.SYSTEM_FROM, 
            settings.ADMINS, 
            newMail.as_string()
        )
        smtp.quit()
    except(smtplib.SMTPException), e:
        l.critical('SMTP Exception: %s' % str(e))
        return False
    finally:
        l.info('Email sent to admins: %s' % ', '.join(settings.ADMINS))

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
