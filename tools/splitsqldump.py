#!/usr/bin/env python

LOG_FILE = 'splitsqldump.py'
LOG_MAX_BYTES = 200000
LOG_MAX_COPIES = 2

import sys
import re
import logging
from logging import handlers
import argparse

# Setup logging
logFormat = '%(asctime)s %(filename)s[%(process)s] %(levelname)s: %(message)s'
logging.basicConfig(
    format=logFormat,
    filename=LOG_FILE,
    level=logging.INFO,
)
l = logging.getLogger(__name__)
h = handlers.RotatingFileHandler(
    LOG_FILE, 
    maxBytes=LOG_MAX_BYTES, 
    backupCount=LOG_MAX_COPIES
)
l.addHandler(h)

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
        '-d', '--db', '--database',
        nargs=1,
        metavar='mySpecialDB',
        help='Name of database to extract, will be created as name.sql in cwd'
    )
    parser.add_argument(
        'filename',
        nargs=1,
        metavar='all-databases.sql',
        help='Filename containing database dumps'
    )

    # Parse the arguments
    args = parser.parse_args()

    try:
        sqldump = open(args.filename, 'r')
    except(OSError, IOError), e:
        l.critical('Could not open input file: %s' % sys.argv[1])
    finally:
        l.info('Trying to read from stdin')
        sqldump = sys.stdin

    for line in sqldump:
        if line.startswith('-- Current database'):
            reMatch = re.search('Current database `([^`]+)`', line)
            dbName = reMatch.group(1)
            l.info('Found DB name: %s' % dbName)

if __name__ == '__main__':
    if main():
        sys.exit(0)
    sys.exit(1)
