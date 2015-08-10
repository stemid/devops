#!/usr/bin/env python

from __future__ import print_function

import smtplib
from sys import exit
from email.mime.text import MIMEText
from argparse import ArgumentParser
from hashlib import md5
from platform import node
from datetime import datetime, timedelta

EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

parser = ArgumentParser(
    description=('Nagios check for monitoring the sending of mail through SMTP'
                 ' and measuring the time it takes.'),
    epilog='by Stefan Midjich <swehack@gmail.com>'
)

parser.add_argument(
    '-H', '--host',
    action='store',
    default='localhost',
    help='SMTP server host'
)

parser.add_argument(
    '-p', '--port',
    action='store',
    default='25',
    help='SMTP server port'
)

parser.add_argument(
    '-s', '--sender',
    action='store',
    default='no-reply@nagios',
    help='From address'
)

parser.add_argument(
    '-S', '--subject',
    action='store',
    default='Nagios monitoring mail',
    help='Subject of monitoring mail'
)

parser.add_argument(
    '-r', '--rcpt',
    action='store',
    default='monitoring@localhost',
    help='To address'
)

parser.add_argument(
    '-L', '--local-hostname',
    action='store',
    default=node(),
    help='Local hostname of sender'
)

parser.add_argument(
    '-l', '--ssl',
    action='store_true',
    default=False,
    help='Use SSL directly'
)

parser.add_argument(
    '-T', '--starttls',
    action='store_true',
    default=False,
    help='Issue starttls during session'
)

parser.add_argument(
    '-A', '--auth',
    action='store_true',
    default=False,
    help='Use SMTP authentication'
)

parser.add_argument(
    '-U', '--username',
    action='store',
    help='SMTP Auth username'
)

parser.add_argument(
    '-P', '--password',
    action='store',
    help='SMTP Auth password'
)

parser.add_argument(
    '-f', '--file',
    type=file,
    help='File with content for mail'
)

parser.add_argument(
    '-t', '--timeout',
    action='store',
    type=int,
    default=30,
    help='Timeout value for SMTP connection'
)

parser.add_argument(
    '-v', '--verbose',
    action='count',
    default=False,
    help='Verbose output. Use more v\'s to increase level of verbosity'
)

args = parser.parse_args()

checksum = md5()
checksum.update(bytes(args.host))
checksum.update(bytes(args.sender))
checksum.update(bytes(args.rcpt))

if args.file is None:
    payload = '''Hi

    This is an automatic monitoring e-mail.

    checksum: {checksum}'''
else:
    payload = args.file.read()

payload = payload.format(checksum=checksum.hexdigest())

msg = MIMEText(payload)
msg['Subject'] = args.subject
msg['From'] = args.sender
msg['To'] = args.rcpt

starttime = datetime.now()

if args.verbose > 1:
    print('Mail submission started at {starttime}'.format(
        starttime=starttime
    ))

if args.ssl:
    if args.verbose:
        print('Connecting with SSL to {host}'.format(host=args.host))

    s = smtplib.SMTP_SSL(
        args.host,
        args.port,
        args.local_hostname,
        args.keyfile,
        args.certfile,
        args.timeout
    )
else:
    if args.verbose:
        print('Connecting to {host}'.format(host=args.host))

    s = smtplib.SMTP(
        args.host,
        args.port,
        args.local_hostname,
        args.timeout
    )

rcpts = []
rcpts.append(args.rcpt)

try:
    if args.auth:
        if args.verbose:
            print('Authenticating on {host} with {username}'.format(
                host=args.host,
                username=args.username
            ))
    else:
        if args.verbose:
            print('Sending mail to {rcpt}'.format(rcpt=args.rcpt))

        s.sendmail(args.sender, rcpts, msg.as_string())
except smtplib.SMTPConnectError as e:
    if args.verbose > 1:
        print(str(e))

    print('CRITICAL: Server did not accept SMTP-connection')
    exit(EXIT_CRITICAL)
except smtplib.SMTPServerDisconnected as e:
    if args.verbose > 1:
        print(str(e))

    # This is when server does not respond at all within timeout
    print('CRITICAL: Server did not respond within {timeout} seconds'.format(
        timeout=args.timeout
    ))
    exit(EXIT_CRITICAL)
except smtplib.SMTPResponseException as e:
    if args.verbose > 1:
        print(str(e))

    print('CRITICAL: Server response was {smtp_code}: {smtp_error}'.format(
        smtp_code=e.smtp_code,
        smtp_error=e.smtp_error
    ))
    exit(EXIT_CRITICAL)
except socket.timeout as e:
    if args.verbose > 1:
        print(str(e))

    print('UNKNOWN: Could not connect to {host} on port {port}'.format(
        host=args.host,
        port=args.port
    ))
    exit(EXIT_UNKNOWN)

endtime = datetime.now()
duration = endtime-starttime

if args.verbose > 1:
    print('Mail submission finished at {datetime}, duration {duration}'.format(
        endtime=endtime,
        duration=duration
    ))

s.quit()

print('OK: Mail submission took {duration}'.format(duration=duration))
exit(EXIT_OK)
