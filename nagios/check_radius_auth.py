#!/usr/bin/env python
# coding: utf-8
# vim: filetype=python
#
# Requires https://github.com/btimby/py-radius/
#
# by Stefan Midjich <swehack@gmail.com> - 2016

from __future__ import print_function

from sys import exit, stderr
from argparse import ArgumentParser

import radius

parser = ArgumentParser()

parser.add_argument(
    '-v', '--verbose',
    action='count',
    default=False,
    dest='verbose',
    help='Verbose output, use more v\'s to increase level'
)

parser.add_argument(
    '-t', '--timeout',
    default=30,
    type=int,
    help='Connection timeout value'
)

parser.add_argument(
    '-H', '--host',
    required=True,
    help='RADIUS Authserver hostname'
)

parser.add_argument(
    '-P', '--port',
    default=1812,
    type=int,
    help='Port number of RADIUS server'
)

parser.add_argument(
    '-S', '--secret',
    required=True,
    help='RADIUS secret for connection'
)

parser.add_argument(
    '-U', '--username',
    required=True,
    help='RADIUS username'
)

parser.add_argument(
    '--password',
    default='garbage',
    help='Auth password'
)

args = parser.parse_args()

# Nagios exit codes
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

with radius.connect((args.host, args.port), args.secret, args.timeout) as conn:
    result = None
    try:
        result = conn.authenticate(args.username, args.password)
    except Exception as e:
        print('CRITICAL: Authentication failed: {error}'.format(
            error=str(e)
        ))
        exit(CRITICAL)

    if not result:
        print('WARNING: Authentication failed')
        exit(WARNING)

    print('OK: Authentication success')
    exit(OK)
