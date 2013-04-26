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

from sys import exit

# Local configuration
DSBROWSE = '/usr/lib/vmware-vcli/apps/host/dsbrowse.pl'
VI_CONFIG = '/usr/lib/nagios/plugins/vmware.cfg'

# Nagios Exit codes
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

def main(args):
    import subprocess

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
            print('UNKNOWN: No datastores found')
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
                available_space.rstrip(' GB')
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
            print('CRITICAL: Datastore %s has %d of %d GB available' % (
                datastore['datastore_name'],
                datastore['available_space'],
                datastore['maximum_capacity']
            ))
            return EXIT_CRITICAL

        if args.warning > percent_left:
            print('WARNING: Datastore %s has %d of %d GB available' % (
                datastore['datastore_name'],
                datastore['available_space'],
                datastore['maximum_capacity']
            ))
            return EXIT_WARNING

    # All is OK, no datastore reached threshold values.
    if args.name == datastores[0]['datastore_name']:
        print('OK: %s has %d available of %d GB total space' % (
            datastores[0]['datastore_name'],
            datastores[0]['available_space'],
            datastores[0]['maximum_capacity']
        ))
    else:
        print('OK: All checked datastores OK')
    return EXIT_OK

# Handle command line arguments
if __name__ == '__main__':
    try:
        from argparse import ArgumentParser
    except:
        from optparse import OptionParser as ArgumentParser

    # Init arguments
    parser = ArgumentParser(
        description = 'Nagios script to check datastore sizes'
    )

    try:
        add_argument = parser.add_argument
    except:
        add_argument = parser.add_option

    add_argument(
        '-f',
        '--config',
        default = VI_CONFIG,
        help = 'VI_CONFIG configuration for vSphere CLI (default: %s)' % VI_CONFIG
    )

    add_argument(
        '-n',
        '--name',
        help = 'Datastore name (default: Check all datastores)'
    )

    add_argument(
        '-w',
        '--warning',
        type = float,
        default = 15.0,
        help = 'Warning threshold in percent, of available space (default: 15)'
    )

    add_argument(
        '-c',
        '--critical',
        type = float,
        default = 10.0,
        help = 'Critical threshold in percent, of available space (default: 10)'
    )

    try:
        (options, args) = parser.parse_args()
    except(TypeError):
        options = parser.parse_args()

    exit(main(options))
