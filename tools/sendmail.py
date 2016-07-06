from __future__ import print_function

import smtplib
from email.utils import formatdate
from sys import stdout, stdin, exit
from argparse import ArgumentParser, FileType
from logging import Formatter, getLogger, DEBUG, WARN, INFO
from logging import StreamHandler

formatter = Formatter('%(asctime)s: %(message)s')
l = getLogger('sendmail.py')
h = StreamHandler(stdout)
h.setFormatter(formatter)
l.addHandler(h)
l.setLevel(INFO)

parser = ArgumentParser()

parser.add_argument(
    '--server',
    required=True,
    help='Sending SMTP server'
)

parser.add_argument(
    '--mail-from',
    required=True,
    help='MAIL FROM'
)

parser.add_argument(
    '--rcpt-to',
    nargs='+',
    help='RCPT TO, can specify more than once'
)

parser.add_argument(
    '--subject',
    default='',
    help='Subject'
)

parser.add_argument(
    '--body-file',
    type=FileType('r'),
    help='Message body, if not specified read from stdin'
)

parser.add_argument(
    '--header',
    nargs='*',
    help='Additional headers, can specify more than once'
)

parser.add_argument(
    '--skip-standard-headers',
    default=False,
    action='store_true',
    help='Skip including of standard headers (MAIL FROM, To, Subject) in message body'
)

parser.add_argument(
    '-v', '--verbose',
    action='count',
    default=False,
    dest='verbose',
    help='Verbose output, use more v\'s to increase level'
)

args = parser.parse_args()

if args.body_file:
    message_body = args.body_file.read()
else:
    if args.verbose:
        l.info('Enter message body, end with EOL (Ctrl+d):')
    message_body = stdin.read()

message_headers = ''
for header in args.header:
    message_headers += str(header)

standard_headers = '''From: {mail_from}
To: {rcpt_to}
Subject: {subject}'''.format(
    now=formatdate(),
    mail_from=args.mail_from,
    rcpt_to=','.join(args.rcpt_to),
    subject=args.subject
)

if not args.skip_standard_headers:
    message = standard_headers
else:
    message = ''

message += """
Date: {date}
{headers}

{body}
""".format(
    date=formatdate(),
    headers=message_headers,
    body=message_body
)

server = smtplib.SMTP(args.server)
if args.verbose:
    server.set_debuglevel(True)

server.sendmail(args.mail_from, args.rcpt_to, message)
server.quit()
