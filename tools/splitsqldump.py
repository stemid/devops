#!/usr/bin/env python

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
        default='mysql', # TODO: PG
        metavar='mysql',
        help='Type of dump to parse, currently only mysql supported'
    )
    parser.add_argument(
        '-d', '--db', '--dbname', '--database',
        nargs=1,
        default='',
        metavar='mySpecialDB',
        help='Name of database to extract, will be created as name.sql in cwd'
    )
    parser.add_argument(
        '-o', '--out', '--output',
        metavar='newdump.sql',
        help='Name of output file'
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

    if args.output and args.

    try:
        sqldump = open(args.filename, 'r')
    except(OSError, IOError), e:
        l.critical('Could not open input file: %s' % sys.argv[1])
    finally:
        l.info('Trying to read from stdin')
        sqldump = sys.stdin

    newDump = None
    # Loop through lines of db dump
    for line in sqldump:
        if line.startswith('-- Current database'):
            dbName = ''

            # Close any previously split db.
            if newDump is not None:
                if newDump.closed is False:
                    newDump.close()

            reMatch = re.search('Current database `([^`]+)`', line)
            dbName = reMatch.group(1)
            l.info('Found DB name: %s' % dbName)
            if dbName == '':
                l.info('Do not support blank db names')
                continue

if __name__ == '__main__':
    if main():
        sys.exit(0)
    sys.exit(1)
