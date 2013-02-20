#!/usr/bin/env python
# See README.md for more info.
# Configuration settings in settings.py
# By Stefan.Midjich@cygate.se 2012

# Import python libs
from sys import stdin, exit
import os
from tempfile import mkstemp
import email
from email.parser import Parser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from logging import handlers, Formatter, getLogger, DEBUG, WARN, INFO

# Import configuration
import settings

# Setup logging
formatter = Formatter(settings.LOG_FORMAT)
l = getLogger(__name__)
h = handlers.RotatingFileHandler(
    settings.LOG_FILE, 
    maxBytes=settings.LOG_MAX_BYTES, 
    backupCount=settings.LOG_MAX_COPIES
)
h.setFormatter(formatter)
l.addHandler(h)
l.setLevel(DEBUG)

def main(f=None):
    # Just a little trick for debugging from REPL
    if f is not None:
        fObject = f
    else:
        fObject = stdin

    # Initialize our working environment
    if initDir(
        settings.TMP_DIR, 
        settings.PROC_EUID, 
        settings.PROC_EGID, 
        0750
    ) is False:
        l.critical('Failed to init working dir: %s' % settings.TMP_DIR)
        return False

    if initDir(
        settings.SPAM_DIR, 
        settings.PROC_EUID, 
        settings.PROC_EGID, 
        0750
    ) is False:
        l.critical('Failed to init working dir: %s' % settings.SPAM_DIR)
        return False

    if initDir(
        settings.HAM_DIR, 
        settings.PROC_EUID, 
        settings.PROC_EGID, 
        0750
    ) is False:
        l.critical('Failed to init working dir: %s' % settings.HAM_DIR)
        return False
    # Finished setting up working directories

    # Read email from stdin
    try:
        inMail = Parser().parse(fObject)
    except(email.errors.MessageParseError, email.errors.HeaderParseError), e:
        l.critical('Could not parse email: %s' % str(e))
        return False

    l.info('Received email: from[%s], subject[%s]' % (inMail.get('from'),
                                                      inMail.get('subject')))

    # First find out if it's a command from an admin, and act on that.
    # TODO: Dynamic command definitions
    if (inMail.get('Subject').startswith('!HAM ') or
        inMail.get('Subject').startswith('!SPAM ') or
        inMail.get('Subject').startswith('!DELETE ')):
        l.debug('Found admin command in subject: %s' % inMail.get('Subject'))
        try:
            if procAdminCmd(inMail):
                return True
        except(AdminError), e:
            l.critical('Caught administrative exception: %s' % str(e))
            return False
        
        l.debug('Admin command did not pan out, proceeding')

    # If it's not multipart at this point, simply give up.
    # Admins are allowed to send non-multipart commands. 
    if inMail.is_multipart() is False:
        l.debug('Non-multipart, discarding mail from: %s' % inMail.get('From'))
        return True

    # Take first payload from incoming mail
    inPayloads = inMail.get_payload()
    if len(inPayloads) < 2:
        l.critical('Must have at least one attachment in incoming mail.')
        return False

    # Skip the first payload assuming it is the sender mail
    inPayloads = inPayloads[1:]

    # At this point we will handle each payload as a separate 
    # spam candidate. 
    for p in inPayloads:
        # Only proceed if the payload is in a valid format.
        if p.get_content_type() in settings.VALID_FORMATS:
            try:
                sendAdminMail(settings.ADMINS, p)
            except(AdminError), e:
                l.critical('Admin error: %s' % str(e))

    return True

# This handles processing of the candidate payloads 
# and notifications to admins. 
def sendAdminMail(rcpts=None, payload=None):
    # Create temporary file for incomming email
    try:
        emailFile = mkstemp(
            dir=settings.TMP_DIR, 
            prefix=settings.TMP_PREFIX
        )
        # Extract the random suffix given to us by tempfile
        tmpSuffix = os.path.basename(emailFile[1])[len(settings.TMP_PREFIX):]
        emailFile = os.fdopen(emailFile[0], 'wb')
    except(OSError, IOError), e:
        raise AdminError('Could not create temporary email file: %s' % str(e))
        return False
    finally:
        l.debug('Created temporary suffix ID for email: %s' % tmpSuffix)

    # Write payload to tmpfile. This should include all 
    # the payloads of the attached spam. 
    # NOTE: Each payload is in fact a tree of payloads. 
    emailFile.write(payload.as_string())
    emailFile.close()
    l.debug('Wrote temporary email file: %s' % emailFile.name)

    # Create the new mail
    newMail = MIMEMultipart()

    # Need to learn how to use __setitem__ with dictionary 
    # mapping style instead. 
    newMail.add_header('From', settings.SYSTEM_FROM)
    newMail.add_header('Reply-to', settings.SYSTEM_REPLY_TO)
    newMail.add_header('Subject',
                       settings.SYSTEM_SUBJECT.format(spamID=tmpSuffix))
    newMail.add_header('To', ','.join(settings.ADMINS))
    newMail.preamble = 'You need a MIME mail reader to read this mail.'

    # Add header to payload and make it an attachment file
    payload.add_header(
        'Content-Disposition', 
        'attachment',
        filename='Viruskandidat_%s.eml' % tmpSuffix
    )
    # Attach the payload to main message
    newMail.attach(payload)
    l.info('Payload attached to new mail: %s' % payload.get_content_type())

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
        raise AdminError('SMTP Exception: %s' % str(e))
        return False
    finally:
        l.info('Email sent to admins: %s' % ', '.join(settings.ADMINS))

    return True

# Administration function to process command mails.
# Raises AdminError exception if execution should stop. 
# Most likely execution should stop because otherwise 
# the incoming mail keeps being processed as a spam
# candidate. 
def procAdminCmd(e=None):
    import re

    cmd = None
    arg = None

    if e is None:
        raise AdminError('Squawk! Polly shouldn\'t be!')
        return False

    # First extract the sender mail address
    try:
        m = re.search('<([^\s\t\r\n]+)>$', e['from'])
        senderEmail = m.group(1)
        l.debug('Found sender email: %s' % senderEmail)
    except(re.error, IndexError), e:
        raise AdminError('Malformed sender address: %s' % str(e))
        return False

    # Do we have an admin?
    if senderEmail.lower() in settings.ADMINS:
        # Extract command from subject
        try:
            m = re.search('!(SPAM|HAM|DELETE)\s+([A-Za-z0-9_]+)', e.get('subject'))
            cmd = m.group(1)
            arg = m.group(2)
            l.debug('Extracted cmd[%s], arg[%s]' % (cmd, arg))
        except(re.error, IndexError), e:
            raise AdminError('Malformed command: %s' % str(e))
            return False

    if arg == '':
        return False

    if cmd == 'SPAM':
        try:
            os.rename(
                '%s/%s%s' % (
                    settings.TMP_DIR, 
                    settings.TMP_PREFIX,
                    arg
                ), 
                '%s/%s%s' % (
                    settings.SPAM_DIR, 
                    settings.SPAM_PREFIX,
                    arg
                )
            )
            l.info('Confirmed spam: %s/%s%s' % (
                settings.SPAM_DIR,
                settings.SPAM_PREFIX,
                arg
            ))
            return True
        except(OSError), e:
            raise AdminError('Move file: %s: %s' % (arg, str(e)))
            return False

    if cmd == 'HAM':
        try:
            os.rename(
                '%s/%s%s' % (
                    settings.TMP_DIR, 
                    settings.TMP_PREFIX,
                    arg
                ),
                '%s/%s%s' % (
                    settings.HAM_DIR,
                    settings.HAM_PREFIX,
                    arg
                )
            )
            l.info('Confirmed ham: %s/%s%s' % (
                settings.TMP_DIR,
                settings.TMP_PREFIX,
                arg
            ))
            return True
        except(OSError), e:
            raise AdminError('Move file: %s: %s' % (arg, str(e)))
            return False

    if cmd == 'DELETE':
        try:
            os.remove('%s/%s%s' % (
                settings.TMP_DIR,
                settings.TMP_PREFIX,
                arg
            ))
            l.info('Deleting file: %s/%s%s' % (
                settings.TMP_DIR,
                settings.TMP_PREFIX,
                arg
            ))
            return True
        except(OSError), e:
            raise AdminError('Delete file: %s: %s' % (arg, str(e)))
            return False

    # Return false and proceed with execution by default
    return False

# Helper function to create directories
def initDir(d=None, dirowner=0, dirgroup=0, dirmode=0000):
    # Check if dir exists first
    try:
        dirStat = os.stat(d)
    except(OSError, IOError), e:
        l.info('Directory does not exist or is unreadable: %s' % d)
        # Try creating dir
        try:
            os.mkdir(d, dirmode)
        except(OSError, IOError), e:
            l.critical('Could not create directory: %s' % (d, str(e)))
            return False
        finally:
            dirStat = os.stat(d)

    # Check its permissions
    if dirStat.st_uid != dirowner or dirStat.st_gid != dirgroup:
        try:
            os.chown(d, dirowner, dirgroup)
        except(OSError, IOError), e:
            l.critical('Could not set owner of directory: %s: %s' %
                       (d, str(e)))
            return False
    return True

# Admin exception for procAdminCmd() function
# I really only wanted the main() execution to proceed so 
# I used an exception for this. A more dynamic return value
# could have worked too. 
class AdminError(Exception):
    def __init__(self, errstr):
        self.errstr = errstr

    def __str__(self):
        return repr(self.errstr)

if __name__ == '__main__':
    if main():
        exit(0)
    exit(1)
