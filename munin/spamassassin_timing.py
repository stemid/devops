#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import glob
import re

graph_category = 'antispam'

if len(sys.argv) > 1:
    if sys.argv[1] == 'config':
        output_string = ('host_name {host_name}\n'
                         'graph_title {graph_title}\n'
                         'graph_category {graph_category}\n'
                         'graph_vlabel seconds\n'
                         'average.label seconds\n'
                         'max.label seconds\n'
                         'min.label seconds\n'
                        )

        print(output_string.format(
            host_name = os.environ['FQDN'],
            graph_title = os.environ.get('graph_title', 'Average scan time'),
            graph_category = graph_category
        ))
        sys.exit(0)

try:
    statefile_name = os.environ.get('statefile', '{0:s}/{1:s}'.format(
        os.environ['MUNIN_PLUGSTATE'],
        os.environ.get('statefile', 'munin-spamtime.state')
    ))
    logfile_name = "{0:s}/{1:s}".format(
        os.environ.get('logdir', '/var/log'),
        os.environ.get('logfile', 'maillog')
    )
except KeyError:
    print('Please configure plugin', file=sys.stderr)
    sys.exit(1)

position = 0
max_s = 0
min_s = 0
average_s = 0
try:
    statefile_size = os.stat(statefile_name).st_size
    with open(statefile_name) as statefile:
        (position, max_s, min_s, average_s) = statefile.readline().split(':')
except (OSError, ValueError) as e:
    position = 0

try:
    logfile_size = os.stat(logfile_name).st_size
except OSError as e:
    print(
        'Logfile {0:s}: {1:s}'.format(logfile_name, str(e)), 
        file=sys.stderr
    )
    sys.exit(1)

# If position is beyond size of logfile
if logfile_size < position:
    # Get list of other logfiles with alternate suffixes
    logfiles = glob.glob('%s*' % logfile_name)
    # Sort the list alphanumerically
    sorted(
        logfiles,
        key=lambda item: (int(item.partition(' ')[0])
                          if item[0].isdigit() else float('inf'), item)
    )

    # Use the last file in the list
    logfile_name = logfiles[-1]
    # TODO: This probably won't work for logfile.0 style.
    # I wrote this with RHEL6 in mind where logrotate suffixes dates.

    try:
        logfile_size = os.stat(logfile_name).st_size
    except OSError as e:
        print(
            'Logfile {0:s}: {1:s}'.format(logfile_name, str(e)), 
            file=sys.stderr
        )
        sys.exit(1)

    position = 0

# Start parsing logfile
logfile = open(logfile_name)
logfile.seek(position)

times = []
for line in logfile:
    if 'TIMING-SA' not in line:
        continue

    regex = r'TIMING-SA total (\d+) ms'
    matched = re.search(regex, line)
    times.append(int(matched.group(1)))

# Save file position for later
position = logfile.tell()

# Convert list of timing values to integers
#times = sorted([map(int, x) for x in times])
# Sort list
times = sorted(times)

print('average.value %s' % average_s)
print('max.value %s' % max_s)
print('min.value %s' % min_s)

# Calculate average value of parsed time values
average_s = reduce(lambda x, y: x + y, times) / len(times)

# Update statefile
with open(statefile_name, 'w+') as statefile:
    print(
        '{position}:{max_s}:{min_s}:{average_s}'.format(
            position = position, 
            max_s = times[-1]/1000,
            min_s = times[0]/1000,
            average_s = average_s/1000
        ),
        file=statefile
    )

sys.exit(0)
