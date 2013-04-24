#!/usr/bin/env python
# Nagios script to check datastore sizes. 
# This script requires vSphere CLI package, has been tested with 5.1.0. Also 
# requires user setup on vSphere server, and configuration file pointing to 
# vCenter server. 
# This is the same configuration file as esxcli uses. 
#
# Example of vmware.cfg file:
#   VI_PASSWORD=myPass2000
#   VI_SERVER=10.10.20.30
#   VI_USERNAME=domain\svc_vmware_nagios
#
# vSphere CLI package on Linux normally installs dsbrowse.pl into 
# /usr/lib/vmware-vcli/apps/host, adjust path below if required. 
#
# By Stefan Midjich 2013

from __future__ import print_function

from sys import stderr, exit
import subprocess
import argparse

# Local configuration
VI_CONFIG = '/usr/lib/nagios/plugins/vmware.cfg'
DSBROWSE = '/usr/lib/vmware-vcli/apps/host/dsbrowse.pl'

# Nagios Exit codes
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

def main():
    # Init arguments
    parser = argparse.ArgumentParser(
        description = 'Nagios script to check datastore sizes'
    )

    parser.add_argument(
        '-c',
        '--config',
        default = VI_CONFIG,
        help = 'VI_CONFIG configuration for vSphere CLI'
    )

    parser.add_argument(
        '-n',
        '--name',
        help = 'Datastore name'
    )

    parser.add_argument(
        '-W',
        '--warning',
        type = float,
        default = 15.0,
        help = 'Warning threshold in percent, of available space'
    )

    parser.add_argument(
        '-C',
        '--critical',
        type = float,
        default = 10.0,
        help = 'Critical threshold in percent, of available space'
    )

    args = parser.parse_args()

    # Complete command to execute
    dsbrowse_cmd = [
        DSBROWSE,
        '--config',
        args.config,
        '--attributes',
        'name,capacity,freespace'
    ]

    # Append extra arguments to command
    if args.name:
        dsbrowse_cmd.append('--name')
        dsbrowse_cmd.append(args.name)

    # Try executing the command
    try:
        dsbrowse = subprocess.Popen(
            dsbrowse_cmd,
            stdout = subprocess.PIPE
        )
        rc = dsbrowse.returncode
    except:
        return EXIT_UNKNOWN

    # Populate list of datastores by looping through stdout of the command
    datastore_name = None
    old_datastore_name = None
    datastores = []
    for line in dsbrowse.stdout:
        if line.startswith('No Datastores Found'):
            print('Error: No datastores found', file=stderr)
            return EXIT_UNKNOWN

        # Get datastore name
        if line.startswith('Information about datastore '):
            (part1, separator, part2) = line.partition(':')
            if datastore_name:
                old_datastore_name = datastore_name
            datastore_name = part2.strip('\' \r\n')

            # Append new item in list
            datastores.append(dict(datastore_name = datastore_name))

        # Get capacity value
        if line.startswith(' Maximum Capacity'):
            (part1, separator, part2) = line.partition(':')
            maximum_capacity = part2.strip(' \r\n')

            # Subsequent calls to -1 will add to the last list item, 
            # dictionary. 
            datastores[-1]['maximum_capacity'] = float(
                maximum_capacity.rstrip(' MGB')
            )

        # Get freespace value
        if line.startswith(' Available space'):
            (part1, separator, part2) = line.partition(':')
            available_space = part2.strip(' \r\n')

            # Subsequent calls to -1 will add to the last list item, 
            # dictionary. 
            datastores[-1]['available_space'] = float(
                available_space.rstrip(' MGB')
            )

    # Sort the list alphabetically by datastore name. 
    datastores.sort(key=lambda i: i.get('datastore_name'))

    # Now that datastores list is populated, check threshold values. Here we 
    # loop through any item of the list and the first one that fails will 
    # sound the alarm. 
    for datastore in datastores:
        percent_left = (
            datastore['available_space'] / datastore['maximum_capacity']
        ) * 100
        percent_used = 100 - percent_left

        if args.critical > percent_left:
            print('Critical: Datastore %s has %d of %d GB available' % (
                datastore['datastore_name'],
                datastore['available_space'],
                datastore['maximum_capacity']
            ))
            return EXIT_CRITICAL

        if args.warning > percent_left:
            print('Warning: Datastore %s has %d of %d GB available' % (
                datastore['datastore_name'],
                datastore['available_space'],
                datastore['maximum_capacity']
            ))
            return EXIT_WARNING

    print('OK: All checked datastores OK')
    return EXIT_OK

if __name__ == '__main__':
    exit(main())
