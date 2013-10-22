#!/usr/bin/env python
# Count leases in an ISC DHCPd leases file.
# This was written because dhcpstatus kept crashing with OOM errors on a 
# 500M large leases file. All I required was to count the leases but more
# info could be added into the matched_ips dictionary. 
#
# By Stefan Midjich

from sys import exit
import argparse
from netaddr import IPNetwork

arse = argparse.ArgumentParser(
    description = 'Count leases in use for one subnet',
    epilog = 'By Stefan Midjich'
)

arse.add_argument(
    '-q', '--quiet',
    action = 'store_true',
    help = 'Only show number of addresses that match'
)

arse.add_argument(
    '-f', '--filename',
    metavar = '/var/lib/dhcp/dhcpd.leases',
    type = argparse.FileType('r'),
    help = 'Leases filename'
)

arse.add_argument(
    'subnet',
    metavar = '10.11.12.13/29',
    help = 'Subnet or ip-address in a subnet'
)

args = arse.parse_args()

try:
    ip = IPNetwork(args.subnet)
    range_ips = list(ip)
except:
    arse.print_usage()
    exit(1)

valid_ips = []
for _ip in range_ips:
    valid_ips.append(str(_ip))

matched_ips = {}
for line in args.filename:
    if line.startswith('lease '):
        (junk, current_ip, junk) = line.split(' ')
        if current_ip in valid_ips:
            try:
                matched_ips[current_ip]['count'] += 1
            except:
                matched_ips[current_ip] = {
                    'count': 1
                }

if args.quiet:
    print len(matched_ips)
else:
    print "Found %d leases out of %d, for subnet %s" % (
        len(matched_ips), 
        len(valid_ips),
        args.subnet
    )
