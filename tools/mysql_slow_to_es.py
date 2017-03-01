#!/usr/bin/env python3
# coding: utf-8

import re
import pytz
from datetime import datetime
from argparse import ArgumentParser, FileType
from configparser import RawConfigParser

from elasticsearch import Elasticsearch

default_timezone = 'Europe/Amsterdam'
default_index = 'mysql-slow'

parser = ArgumentParser()

parser.add_argument(
    '-c', '--config',
    required=True,
    type=FileType('r'),
    help='Configuration file'
)

parser.add_argument(
    '-v', '--verbose',
    action='count',
    default=False,
    dest='verbose',
    help='Verbose output, use more v\'s to increase level'
)

parser.add_argument(
    '--date-format',
    default='%y%m%d %H:%M:%S',
    metavar='DATE_FORMAT',
    help='Mysql slow log Timestamp format according to strftime'
)

parser.add_argument(
    '--start-from',
    metavar='DATE',
    help=('Start importing docs from this date. Uses same date format to '
          'parse as is specified with --date-format. This is useful when '
          'you want to continue parsing a file from a certain time '
          'because otherwise the script will create duplicate documents '
          'in Elasticsearch.')
)

parser.add_argument(
    'logfile',
    type=FileType('r', encoding='ISO-8859-1'),
    help='Mysql slow log file'
)

parser.add_argument(
    '-D', '--dry-run',
    action='store_true',
    default=False,
    help=('Only print what would be inserted into Elasticsearch, do not'
          ' insert anything')
)


def doc_exists(es, doc):
    res = es.search(index=default_index, body=doc)

    if res['hits']['total'] > 0:
        return True
    return False


class ProcessLog(object):

    def __init__(self, **kwargs):
        self._date_format = kwargs.get('date_format')
        self._time = None
        self._summary = []

        self._query_info = {}
        self._user_info = {}
        self.ready = False


    def _parse_time(self, line):
        m = re.match(r'^# Time: (\d+)[\t\s]+([\d\:]+)', line)

        if not m:
            return None

        try:
            dt = datetime.strptime(
                '{date} {time}'.format(
                    date=m.group(1),
                    time=m.group(2)
                ),
                self._date_format
            )
        except Exception as e:
            print('Exception: {error}'.format(
                error=str(e)
            ))
            return None

        return dt
    

    def _parse_user(self, line):
        regex = r'^# User@Host: ([^\b@]+)[\t\s]+@[\t\s]+\[([\d\.]+)\]'
        m = re.match(regex, line)

        if not m:
            return None

        return {
            'username': m.group(1),
            'ip-address': m.group(2)
        }


    def _parse_query(self, line):
        regex = ('# Query_time: (\d+\.\d+)\s+'
                 'Lock_time: (\d+\.\d+)\s+'
                 'Rows_sent: (\d+)\s+'
                 'Rows_examined: (\d+)')
        m = re.match(regex, line)

        if not m:
            print('No amtch')
            return None

        return {
            'query-time': float(m.group(1)),
            'block-time': float(m.group(2)),
            'rows-sent': int(m.group(3)),
            'rows-examined': int(m.group(4))
        }


    def process_line(self, line):
        if line.startswith('# Time: '):
            self.time = self._parse_time(line)

        if line.startswith('# User@Host: '):
            self._user_info = self._parse_user(line)

        if line.startswith('# Query_time: '):
            self.query_info = self._parse_query(line)


    def commit(self):
        self._summary.append({
            'query_info': self._query_info,
            'user_info': self._user_info,
            'date': self._time
        })

        self._query_info = {}
        self._user_info = {}
        self.ready = False

        
    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, val):
        self._time = val


    @property
    def query_info(self):
        return self._query_info

    @query_info.setter
    def query_info(self, val):
        self._query_info = val
        self.ready = True


    @property
    def user_info(self):
        if not self._user_info:
            return {}
        return self._user_info


    @property
    def summary(self):
        return self._summary


    @property
    def last(self):
        if len(self._summary):
            return self._summary[-1]


def main(args, config):
    es_servers = []

    server_string = '{protocol}://{hostname}:{port}'.format(
        protocol=config.get('elasticsearch', 'protocol'),
        hostname=config.get('elasticsearch', 'hostname'),
        port=config.getint('elasticsearch', 'port')
    )
    es_servers.append(server_string)
    es = Elasticsearch(es_servers)

    p = ProcessLog(
        date_format=args.date_format
    )

    start_from = None
    if args.start_from:
        start_from = datetime.strptime(
            args.start_from,
            args.date_format
        )

    total_docs = 0
    skipped_docs = 0
    created_docs = 0
    for line in args.logfile:
        p.process_line(line)

        if p.ready:
            total_docs += 1

            if start_from:
                if p.time < start_from:
                    if args.verbose > 1:
                        print('Skipping doc due to start-time')

                    skipped_docs += 1
                    continue

            local_tz = pytz.timezone(default_timezone)
            local_dt = local_tz.localize(p.time, is_dst=None)
            utc_dt = local_dt.astimezone(pytz.utc)

            try:
                es_doc = {
                    'timestamp': utc_dt,
                    'username': p.user_info['username'],
                    'ip-address': p.user_info['ip-address'],
                    'query-time': p.query_info['query-time'],
                    'block-time': p.query_info['block-time'],
                    'rows-sent': p.query_info['rows-sent'],
                    'rows-examined': p.query_info['rows-examined']
                }
            except KeyError as e:
                if args.verbose > 1:
                    raise
                continue

            search_matches = [
                { 'match': {'timestamp': utc_dt} },
                #{ 'match': {'username': p.user_info['username']} },
                #{ 'match': {'ip-address': p.user_info['ip-address']} },
                { 'match': {'query-time': p.query_info['query-time']} },
                #{ 'match': {'block-time': p.query_info['block-time']} },
                #{ 'match': {'rows-examined': p.query_info['rows-examined']} },
                #{ 'match': {'rows-sent': p.query_info['rows-sent']} },
            ]
            search_doc = {
                'query': {
                    'bool': {
                        'must': search_matches
                    }
                }
            }
            # Not sure if this works as it should.
            #if doc_exists(es, search_doc):
            #    if args.verbose:
            #        print('Document exists: {doc}'.format(
            #            doc=repr(es_doc)
            #        ))
            #    skipped_docs += 1
            #    continue

            if args.dry_run:
                print(p.last)
            else:
                res = es.index(
                    index=default_index,
                    doc_type='log',
                    body=es_doc
                )

                if args.verbose:
                    print('Created ES index: {res}'.format(
                        res=repr(res)
                    ))
                created_docs += 1

            p.commit()

    if args.verbose:
        print('Created {created}, skipped {skipped} out of total {total}'.format(
            created=created_docs,
            skipped=skipped_docs,
            total=total_docs
        ))


if __name__ == '__main__':
    args = parser.parse_args()
    config = RawConfigParser()
    config.readfp(args.config)

    main(args, config)
