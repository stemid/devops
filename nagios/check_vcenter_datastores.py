#!/usr/bin/env python3
# coding: utf-8
# Nagios monitoring script for vcenter datastores.
#
# Configuration can look like this:
# [vcenter]
# hostname = 127.0.0.1
# username = service_accountname
# password = secret password
# port = 443
#
# by Stefan Midjich 2016

import atexit
import math
from sys import exit, stderr
from fnmatch import fnmatch
from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from pprint import pprint
from operator import itemgetter as i
from functools import cmp_to_key

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

config = ConfigParser()
#config.readfp(open('vcenter_defaults.cfg'))
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
    type=FileType('r'),
    dest='config_file',
    help='Additional configuration options'
)

parser.add_argument(
    '-i', '--include',
    dest='include',
    default=[],
    nargs='+',
    help=('Include datastores matching this pattern. Pattern uses fnmatch '
          'so you can use * as wildcard for entire strings and ? as wildcard '
          'for single characters.')
)

parser.add_argument(
    '-x', '--exclude',
    dest='exclude',
    default=[],
    nargs='*',
    help=('Exclude datastores matching this pattern, excludes override'
          ' includes.')
)

parser.add_argument(
    '-W', '--warning',
    type=int,
    default=90,
    metavar='%',
    help='Warning threshold in percent of used space.'
)

parser.add_argument(
    '-C', '--critical',
    type=int,
    default=95,
    metavar='%',
    help='Critical threshold in percent of used space.'
)

parser.add_argument(
    '-O', '--overcommitted',
    type=int,
    default=0,
    metavar='%',
    help='Alert if any datastore is overcommitted by this percentage.'
)

parser.add_argument(
    '-m', '--max-alerts',
    type=int,
    default=4,
    metavar='NUMBER',
    help='Number of alerts to show before cutting off output and abbreviating.'
)


def convertSize(size):
   if (size == 0):
       return '0B'
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size,1024)))
   p = math.pow(1024,i)
   s = round(size/p,2)
   return '%s %s' % (s,size_name[i])


def multikeysort(items, columns):
    comparers = [
        (
            (
                i(col[1:].strip()), -1
            ) if col.startswith('-') else (i(col.strip()), 1)
        )
        for col in columns
    ]

    def comparer(left, right):
        comparer_iter = (
            cmp(fn(left), fn(right)) * mult
            for fn, mult in comparers
        )
        return next((result for result in comparer_iter if result), 0)
    return sorted(items, key=cmp_to_key(comparer))


def get_datastores(si, include, exclude):
    datastores = []
    content = si.RetrieveContent()
    for dc in content.rootFolder.childEntity:
        for ds in dc.datastore:
            exclude_matches = [e for e in exclude if fnmatch(ds.name, e)]
            include_matches = [i for i in include if fnmatch(ds.name, i)]

            print(include_matches)
            print(exclude_matches)
            exit(1)
            if exclude and fnmatch(ds.name, exclude):
                continue
            if fnmatch(ds.name, include):
                summary = ds.summary
                # Convert from bytes to KB so my convertSize function works
                datastores.append({
                    'name': summary.name,
                    'capacity': float(summary.capacity),
                    'freeSpace': float(summary.freeSpace),
                    'uncommitted': float(summary.uncommitted)
                })

    return datastores


def print_datastore(ds):
    print(('{name}: Free {free_gb}[{free}%], '
           'Used {used_gb}[{used}%], '
           'Uncommitted {uncommitted_gb}[{uncommitted}%], '
           'Total {total} (Overcommitted {overcommitted}%)').format(
               used_gb=convertSize(ds.get('used_bytes')),
               used=ds.get('used'),
               overcommitted=ds.get('overcommitted'),
               free_gb=convertSize(ds.get('freeSpace')),
               uncommitted_gb=convertSize(ds.get('uncommitted')),
               name=ds.get('name'),
               free=ds.get('free'),
               uncommitted=ds.get('uncommitted_percent'),
               total=convertSize(ds.get('capacity'))
           )
         )


# This handles Nagios alerts
# TODO: Monitorscout handler
def handle_alerts(ds):
    args = parser.parse_args()

    datastores = multikeysort(ds, ['overcommitted', 'used'])

    if datastores[0].get('used') > args.critical:
        out_msg = 'CRITICAL: '
        exit_code = 2
    elif datastores[0].get('used') > args.warning:
        out_msg = 'WARNING: '
        exit_code = 1
    elif datastores[0].get('overcommitted') > args.overcommitted:
        out_msg = 'WARNING: '
        exit_code = 1
    else:
        out_msg = 'UNKNOWN: '
        exit_code = 3

    count=0
    for d in datastores:
        if count > args.max_alerts:
            break
        count += 1
        if d.get('overcommitted') > args.overcommitted:
            out_msg += '{name} overcommitted with {perc}% | '.format(
                name=d.get('name'),
                perc=d.get('overcommitted')
            )
        else:
            out_msg += '{name} is {perc}% full | '.format(
                name=d.get('name'),
                perc=d.get('used')
            )

    if len(datastores) > args.max_alerts:
        out_msg += 'Plus alerts on {more} more datastores not shown.'.format(
            more=(len(datastores)-args.max_alerts)-1
        )

    print(out_msg)
    exit(exit_code)


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
            'Could not connect to vcenter server: {0}'.format(
                str(e)
            ),
            file=stderr
        )
        if args.verbose > 1:
            raise Exception(e)
        else:
            exit(2)

    atexit.register(Disconnect, si)

    datastores = []
    datastores = get_datastores(si, include=args.include, exclude=args.exclude)

    alert_ds = []

    # Process dataset of results returned
    for ds in datastores:
        free_percent = int((
            ds.get('freeSpace')/ds.get('capacity')
        ) * 100)
        used_percent = 100-free_percent
        uncommitted_percent = int((
            ds.get('uncommitted')/ds.get('capacity')
        ) * 100)
        overcommitted_space = ds.get('uncommitted')-ds.get('freeSpace')
        overcommitted_percent = int((
            overcommitted_space/ds.get('capacity')
        ) * 100)

        ds['overcommitted'] = overcommitted_percent
        ds['used'] = used_percent
        ds['used_bytes'] = ds.get('capacity')-ds.get('freeSpace')
        ds['free'] = free_percent
        ds['uncommitted_percent'] = uncommitted_percent

        if args.verbose > 1:
            print_datastore(ds)

        if overcommitted_percent > args.overcommitted:
            alert_ds.append(ds)
            continue

        if args.warning < used_percent or args.critical < used_percent:
            alert_ds.append(ds)
            continue

    if len(alert_ds) and args.verbose > 1:
        pprint([len(alert_ds), alert_ds])

    if len(alert_ds):
        handle_alerts(alert_ds)


if __name__ == '__main__':
    main()
