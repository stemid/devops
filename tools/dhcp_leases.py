#!/usr/bin/env python
# Count leases in an ISC DHCPd leases file.
# 
# Script depends on python module netaddr.
#   Install it with pip install netaddr.
# Script also depends on python 2.7 for argparse.
#
# This was written because dhcpstatus kept crashing with OOM errors on a 
# 500M large leases file. All I required was to count the leases but more
# info could be added into the matched_ips dictionary. 
#
# Run dhcp_leases.py -h for more info.
#
# By Stefan Midjich

from sys import exit
import argparse
from netaddr import IPNetwork

def main():
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

    matches = count(args.filename, valid_ips)

    if args.quiet:
        print len(matches)
    else:
        print "Found %d leases out of %d, for subnet %s" % (
            len(matches), 
            len(valid_ips),
            args.subnet
        )

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

if __name__ == '__main__':
    main()
