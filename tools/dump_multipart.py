#!/usr/bin/env python
# Dissect multipart payloads in emails and dump the message in clear text
# instead of base64 encoded chunks. 
# by Stefan Midjich <swehack@gmail.com>

from sys import exit
from argparse import ArgumentParser
from email.parser import Parser


parser = ArgumentParser()

parser.add_argument(
    '-f', '--file',
    type=file,
    dest='mail_file',
    help='Input mail file'
)

args = parser.parse_args()

mail = Parser().parse(args.mail_file)
if mail.is_multipart is False:
    exit(1)

payloads = mail.get_payload()

for payload in payloads:
    if payload.get_content_type() in ['text/html', 'text/plain']:
        print payload.get_payload(decode=True)
    else:
        print payload.get_payload()
