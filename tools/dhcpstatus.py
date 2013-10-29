#!/usr/bin/env python
# Create status info of ISC DHCPd leases in JSON format.
# 
# Depends on python module netaddr.
#   Install with pip install netaddr.
# Depends on iscconf for parsing dhcpd.conf.
#   Install with pip install iscconf
# Depends on python 2.7 for argparse.
#
# This was written because dhcpstatus kept crashing with OOM errors on a 
# 500M large leases file. 
#
# Run dhcpstatus.py -h for more info.
#
# By Stefan Midjich

from __future__ import print_function

from sys import exit, stderr, stdout
from argparse import ArgumentParser, FileType
from json import dumps

from netaddr import IPNetwork
from iscconf import parse

# This does the actual counting of leases in dhcpd.leases. It takes a list of
# valid IP-addresses as argument, and a file object to the leases. 
# Return value is a dictionary of matched leases. 
# Counting can take a long time on big leases files. 
def count(file, valid_ips):
    matched_ips = {}
    for line in file:
        if line.startswith('lease '):
            (junk, current_ip, junk) = line.split(' ')
            if current_ip in valid_ips:
                try:
                    matched_ips[current_ip]['count'] += 1
                except:
                    matched_ips[current_ip] = {
                        'count': 1,
                        'starts': None,
                        'ends': None
                    }
        else:
            if line.lstrip(' ').startswith('starts '):
                (
                    junk1,
                    junk2,
                    date,
                    time
                ) = line.lstrip(' ').split(' ')
                try:
                    matched_ips[current_ip]['starts'] = date
                except:
                    pass
            if line.lstrip(' ').startswith('ends '):
                (
                    junk1,
                    junk2,
                    date,
                    time
                ) = line.lstrip(' ').split(' ')
                try:
                    matched_ips[current_ip]['ends'] = date
                except:
                    pass
    return matched_ips

arse = ArgumentParser(
    description = 'Create JSON statistics of used leases in ISC DHCPd',
    epilog = '''This program works by reading all the shared-network blocks in 
    a dhcpd.conf file. Only subnets in shared-network blocks are processed. 
    
    By Stefan Midjich'''
)

arse.add_argument(
    '-v', '--verbose',
    action = 'store_true',
    help = 'Debugging info'
)

arse.add_argument(
    '-l', '--leases',
    metavar = '/var/lib/dhcp/dhcpd.leases',
    type = FileType('r'),
    help = 'File containing all leases for ISC DHCPd'
)

arse.add_argument(
    '-L', '--list',
    action = 'store_true',
    help = 'Only list available subnets and exit'
)

arse.add_argument(
    '-i', '--indent',
    action = 'store_true',
    help = 'Indent output to prettify it'
)

arse.add_argument(
    '-c', '--configuration',
    metavar = '/etc/dhcp/dhcpd.conf',
    type = FileType('r'),
    help = 'ISC DHCPd Configuration file containing shared-network blocks'
)

arse.add_argument(
    '-o', '--output',
    metavar = '/tmp/dhcpstatus_output.json',
    default = stdout,
    type = FileType('w'),
    help = 'JSON output file for DHCP statistics'
)

arse.add_argument(
    'isp_name',
    metavar = 'ISP-name',
    help = 'Name of shared-network to create statistics for, can be \'any\''
)

args = arse.parse_args()

indent = None
if args.indent:
    indent = 4

try:
    parsed_dhcp_config = parse(args.configuration.read())
except Exception as e:
    print(str(e), file=stderr)
    arse.print_usage()
    exit(1)

# Start building the output dict by reading subnet info for each ISP defined
# in dhcpd.conf as a shared-network.
json_isp = {}
for item in parsed_dhcp_config:
    try:
        (k, v) = item
    except:
        continue
    if k == 'shared-network':
        last_isp = v
        json_isp[last_isp] = {}
        for subitem in parsed_dhcp_config[item]:
            try:
                (sk, sv, sk2, sv2) = subitem
            except:
                continue
            if sk == 'subnet':
                _subnet = sv + '/' + sv2
                try:
                    json_isp[last_isp]['subnets'].append(_subnet)
                except:
                    json_isp[last_isp]['subnets'] = [_subnet]

# Just list the ISPs and their subnets, and exit. 
if args.list:
    if args.isp_name == 'any':
        print(dumps(json_isp, indent=indent), file=args.output)
    else:
        print(dumps(json_isp[args.isp_name], indent=indent), file=args.output)
    exit(0)

# Else proceed with regular execution of the program. 

# Get a list of valid IP-addresses to search the leases for. 
search_ips = []
for subnet in json_isp[args.isp_name]['subnets']:
    _ip = IPNetwork(subnet)
    for _ip_address in list(_ip):
        search_ips.append(str(_ip_address))

matched_ips = count(args.leases, search_ips)

print(dumps(matched_ips, indent=indent), file=args.output)
