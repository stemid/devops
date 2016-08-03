#!/usr/bin/env python
# Nagios script that logs into EWS and lists all calendar events between 14
# days ago and right now. This is meant to ensure EWS is working.
# Requires pytz and pyexchange pip packages.
# Only supports Python 2 for now, pyexchange code is python 3 compatible but
# relies on python-ntlm which might still be in unstable state with python3.
#
# See check_ews_login.py --help for more info.
#
# by Stefan Midjich <swehack at gmail.com> 2016-08-03

from __future__ import print_function

from sys import stderr, exit
from datetime import datetime, timedelta
from argparse import ArgumentParser, FileType
try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
from pprint import pprint as pp

from pytz import timezone
from pyexchange import Exchange2010Service, ExchangeNTLMAuthConnection

parser = ArgumentParser()

parser.add_argument(
    '--url',
    help='EWS URL for example https://webmail.company.tld/EWS/Exchange.asmx'
)

parser.add_argument(
    '--username',
    help='Username like DOMAIN\myuser'
)

parser.add_argument(
    '--password',
    action='store_true',
    help='Read password from stdin'
)

parser.add_argument(
    '--config',
    type=FileType('r'),
    help='Config file'
)

default_config = {
    'url': 'https://localhost/EWS/Exchange.asmx',
    'username': 'DOMAIN\Administrator',
    'password': 'garbage.',
    'timezone': 'Europe/Copenhagen'
}


if __name__ == '__main__':
    args = parser.parse_args()
    config = RawConfigParser(default_config)

    if args.config:
        config.readfp(args.config)
    else:
        config.read(['/etc/check_ews.cfg', './check_ews.cfg'])

    if args.url:
        url = args.url
    else:
        url = config.get('DEFAULTS', 'url')

    if args.username:
        username = args.username
    else:
        username = config.get('DEFAULTS', 'username')

    if args.password:
        password = getpass('> ')
    else:
        password = config.get('DEFAULTS', 'password')

    try:
        connection = ExchangeNTLMAuthConnection(
            url=url,
            username=username,
            password=password
        )
    except Exception as e:
        print('CRITICAL: Could not connect to EWS: {error}'.format(
            error=str(e)
        ))
        exit(2)

    try:
        service = Exchange2010Service(connection)
    except Exception as e:
        print('WARNING: Could not login to EWS: {error}'.format(
            error=str(e)
        ))
        exit(1)

    calendar = service.calendar(id='calendar')
    try:
        start_date = datetime.now() - timedelta(days=14)
        events = calendar.list_events(
            start=timezone(config.get('DEFAULTS', 'timezone')).localize(start_date),
            end=timezone(config.get('DEFAULTS', 'timezone')).localize(datetime.now())
        )
    except Exception as e:
        print('WARNING: Failed to use EWS calendar: {error}'.format(
            error=str(e)
        ))
        exit(1)

    print('OK: EWS is working')
    exit(0)
