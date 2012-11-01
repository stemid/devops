#!/usr/bin/env python
# Wrote this because GNU split can't 
# split by regex and I just wanted 
# a program like this available. 
# Unfortunately argparse requires 
# python 2.7 to work without installing 
# a 3rd party module. 
# Stupid Debian stable. 
#
# by Stefan Midjich
# CC0 - 2012

LOG_FILE = 'splitsqldump.log'
LOG_MAX_BYTES = 200000
LOG_MAX_COPIES = 2

import sys
import re
import logging
from logging import handlers
import argparse

# Setup logging
formatter = logging.Formatter('%(asctime)s %(filename)s[%(process)s] %(levelname)s: %(message)s')
l = logging.getLogger(__name__)
h = handlers.RotatingFileHandler(
    LOG_FILE, 
    maxBytes=LOG_MAX_BYTES, 
    backupCount=LOG_MAX_COPIES
)
h.setFormatter(formatter)
l.addHandler(h)
l.setLevel(logging.INFO)

def main():
    # Initiate argument parser and add arguments
    parser = argparse.ArgumentParser(
        description='Split large SQL dumps',
        epilog='by Stefan.Midjich@cygate.se (CC0 - 2012)'
    )
    parser.add_argument(
        '-t', '--type', '--dbtype',
        nargs=1,
        choices=[
            'mysql',
        ],
        default='mysql', # TODO: PG
        dest='dbtype',
        metavar='mysql',
        help='Type of dump to parse, currently only mysql supported'
    )
    parser.add_argument(
        '-d', '--db', '--dbname', '--database',
        nargs='?', #TODO: Support multiple
        default='',
        dest='dbname',
        metavar='mySpecialDB',
        help='Name of database to extract, will be created as name.sql in cwd'
    )
    parser.add_argument(
        '-s', '--stdout',
        action='store_true',
        dest='stdout',
        help='Output to stdout'
    )
    parser.add_argument(
        'filename',
        nargs='?',
        default='',
        metavar='all-databases.sql',
        help='Filename containing database dumps'
    )

    # Parse the arguments
    args = parser.parse_args()

    try:
        sqldump = open(args.filename, 'r')
    except(OSError, IOError), e:
        l.critical('Could not open input file: %s' % args.filename)
        l.info('Trying to read from stdin')
        sqldump = sys.stdin

    newDump = None
    # Loop through lines of db dump
    for line in sqldump:
        if line.startswith('-- Current Database:'):
            dbName = ''

            # Close any previously split db.
            if newDump is not None and args.stdout is False:
                if newDump.closed is False:
                    newDump.close()

            reMatch = re.search('-- Current Database: `([^`]+)`', line)
            dbName = reMatch.group(1)
            l.info('Found DB name: %s' % dbName)
            if dbName == '':
                l.info('Do not support blank db names')
                continue

            if args.dbname is not None:
                if args.dbname != dbName:
                    if newDump.closed is False: newDump.close()
                    newDump = None
                    continue

            if args.stdout is False:
                try:
                    newDump = open('%s.sql' % dbName, 'w')
                except(OSError, IOError), e:
                    l.critical('Could not open output file: %s.sql' % dbName)
                    return False

        # Write line to file
        if newDump is not None:
            if newDump.closed is False: newDump.write(line)

    return True

if __name__ == '__main__':
    if main():
        sys.exit(0)
    sys.exit(1)
