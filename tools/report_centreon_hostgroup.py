#!/usr/bin/env python
# This script extracts a CSV report of all hosts and their services in a 
# specified hostgroup. 
# By Stefan Midjich

from __future__ import print_function
from sys import stdout, exit
from argparse import ArgumentParser, FileType
from ConfigParser import ConfigParser
from itertools import izip_longest
import MySQLdb as mysql

# Function to get all hosts and services for one hostgroup
def get_hostgroup(conn, hostgroup):
    cursor = conn.cursor()

    # First get all the hosts matching that hostgroup
    rows = cursor.execute('''
                          select host.host_name as hostname, 
                          host.host_id as hostid, host.host_alias as hostalias, 
                          host.host_address as ipaddress
                          from host, hostgroup_relation, hostgroup 
                          where hostgroup.hg_id = hostgroup_relation.hostgroup_hg_id 
                          and host.host_id = hostgroup_relation.host_host_id 
                          and hostgroup.hg_name = %s
                          order by host.host_alias
                          ''',
                          (hostgroup, )
                         )
    if rows <= 0:
        return []

    hosts = cursor.fetchall()
    hosts_data = []

    # Then get all the services for each host
    for (hostname, hostid, hostalias, ipaddress) in hosts:
        rows = cursor.execute('''
                              select host.host_name as hostname, 
                              host.host_alias as hostalias, 
                              service.service_description
                              from service, host_service_relation, host 
                              where host_service_relation.host_host_id = host.host_id 
                              and host.host_id=%s and host_service_relation.service_service_id=service.service_id
                              ''',
                              (hostid, )
                             )

        service_data = []
        if rows > 0:
            services = cursor.fetchall()
            for (hostname, hostalias, service_description) in services:
                service_data.append(service_description)

        hosts_data.append({
            'hostname': hostname,
            'hostid': hostid,
            'hostalias': hostalias,
            'ipaddress': ipaddress,
            'services': service_data,
        })

    return hosts_data
# End of get_hostgroup function

# Initiate argument parser
parser = ArgumentParser(
    description = '''
    Extract CSV reports of all hosts and their services from centreon database.
    ''',
    epilog = 'By Stefan Midjich'
)

parser.add_argument(
    '-c', '--config',
    type = FileType('r'),
    metavar = 'CONFIG_FILE',
    required = True,
    help = 'Specify configuration file with database info.'
)

parser.add_argument(
    '-o', '--output',
    type = FileType('w'),
    metavar = 'OUTPUT_FILE',
    default = stdout,
    help = 'Output into CSV file, or specify - for stdout.'
)

parser.add_argument(
    'hostgroups',
    nargs = '+',
    metavar = 'HOSTGROUP',
    help = 'The hostgroup or hostgroups to get stats for.'
)

opts = parser.parse_args()

# Initiate configuration parser and read configuration file
config = ConfigParser()
config.readfp(opts.config)

# Connect to mysql
conn = mysql.connect(
    host = config.get('main', 'hostname'),
    user = config.get('main', 'username'),
    passwd = config.get('main', 'password'),
    db = config.get('main', 'database'),
    use_unicode = True
)

# Gather up data for CSV conversion
for hostgroup in opts.hostgroups:
    hosts = get_hostgroup(conn, hostgroup)
    
    # Print CSV file header with all hostnames
    print(';'.join(
        map(
            lambda x: '%s (%s)' % (x['hostname'], x['ipaddress']), hosts
        )
    ), file=opts.output)
    service_lists = [item['services'] for item in hosts]
    
    # Print all services for each host
    # Thanks to cdunklau@freenode for help with itertools
    for service in izip_longest(*service_lists, fillvalue=''):
        print(';'.join(map(str, service)), file=opts.output)
