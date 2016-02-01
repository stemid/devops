#!/usr/bin/env python
# coding: utf-8
# Nagios monitoring script for vcenter datastores.
# 
# by Stefan Midjich 2016

from __future__ import print_function

import atexit
from sys import exit, stderr
from fnmatch import fnmatch
from argparse import ArgumentParser
from ConfigParser import ConfigParser
from pprint import pprint

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

config = ConfigParser()
config.readfp(open('vcenter_defaults.cfg'))
config.read(['/etc/vcenter_datastores.cfg', './vcenter_local.cfg'])

parser = ArgumentParser(
    description='Nagios monitoring script for vcenter datastores',
    epilog='Example: ./check_vcenter_datastores.py -c /etc/datastores.cfg'
)

parser.add_argument(
    '-v', '--verbose',
    action='count',
    default=False,
    dest='verbose',
    help='Verbose output, use more v\'s to increase level'
)

parser.add_argument(
    '-c', '--configuration',
    type=file,
    dest='config_file',
    help='Additional configuration options'
)

parser.add_argument(
    '-i', '--include',
    dest='include',
    default='*',
    help=('Include datastores matching this pattern. Pattern uses fnmatch '
          'so you can use * as wildcard for entire strings and ? as wildcard '
          'for single characters.')
)

parser.add_argument(
    '-x', '--exclude',
    dest='exclude',
    help=('Exclude datastores matching this pattern, excludes override'
          ' includes.')
)

parser.add_argument(
    '-W', '--warning',
    default=90,
    help='Warning threshold in percent of used space.'
)

parser.add_argument(
    '-C', '--critical',
    default=95,
    help='Critical threshold in percent of used space.'
)

def get_datastores(si, include, exclude):
    datastores = []
    content = si.RetrieveContent()
    for dc in content.rootFolder.childEntity:
        for ds in dc.datastore:
            if exclude and fnmatch(ds.name, exclude):
                continue
            if fnmatch(ds.name, include):
                summary = ds.summary
                datastores.append({
                    'name': summary.name,
                    'capacity': float(summary.capacity),
                    'freeSpace': float(summary.freeSpace),
                    'uncommitted': float(summary.uncommitted)
                })

    return datastores


def main():
    args = parser.parse_args()

    # Override configuration with file provided on cli
    if args.config_file:
        config.readfp(args.config_file)

    if args.verbose == 2:
        print('Connecting to {0}'.format(
            config.get('vcenter', 'hostname')
        ))
    try:
        # Workaround for unsigned SSL cert
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE

        si = SmartConnect(
            host=config.get('vcenter', 'hostname'),
            user=config.get('vcenter', 'username'),
            pwd=config.get('vcenter', 'password'),
            port=config.getint('vcenter', 'port'),
            sslContext=context
        )
    except Exception as e:
        print(
            'CRITICAL: Could not connect to vcenter server: {0}'.format(
                str(e)
            ),
            file=stderr
        )
        if args.verbose:
            raise Exception(e)
        else:
            exit(2)

    atexit.register(Disconnect, si)

    datastores = []
    datastores = get_datastores(si, include=args.include, exclude=args.exclude)

    # Process list of results
    for ds in datastores:
        free_percent = int((
            ds.get('freeSpace')/ds.get('capacity')
        ) * 100)
        used_percent = 100-free_percent
        uncommitted_percent = int((
            ds.get('uncommitted')/ds.get('capacity')
        ) * 100)
        print('{name}: {free}%, {uncommitted}%, {total}GB'.format(
            name=ds.get('name'),
            free=free_percent,
            uncommitted=uncommitted_percent,
            total=int(ds.get('capacity'))/1024/1024/1024
        ))


if __name__ == '__main__':
    main()
