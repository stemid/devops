#!/usr/bin/env python3
# Monitoring script for MariaDB wsrep cluster state
#
# All configuration is done in check_wsrep.cfg and each section represents
# a wsrep_value to monitor. For example;
# [wsrep_cluster_size]
# default = 3
#
# This example will not let the wsrep_cluster_size deviate from the value 3.
#
# by Stefan Midjich <swehack@gmail.com> - 2016/02

from sys import exit
from configparser import RawConfigParser

import pymysql

config = RawConfigParser({
    'hostname': 'localhost',
    'username': 'dbuser',
    'password': 'dbpass',
    'database': 'dbname'
})
config.read(['/etc/check_wsrep.cfg', './check_wsrep.cfg'])

try:
    conn = pymysql.connect(
        host=config.get('DEFAULT', 'hostname'),
        user=config.get('DEFAULT', 'username'),
        password=config.get('DEFAULT', 'password'),
        db=config.get('DEFAULT', 'database')
    )
except Exception as e:
    print('CRITICAL: Could not connect to database server: {error}'.format(
        error=str(e)
    ))
    exit(2)

cursor = conn.cursor()

try:
    rows = cursor.execute("show status like 'wsrep%'")
except Exception as e:
    print('UNKNOWN: Could not execute query: {error}'.format(
        error=str(e)
    ))
    exit(3)

if rows <= 0:
    print('UNKNOWN: No rows returned, wsrep not configured')
    exit(3)

sections = config.sections()
alerts = []

for (key, value) in cursor:
    if key in sections:
        if value == config.get(key, 'default'):
            continue
        else:
            alerts.append((key, value, config.get(key, 'default')))

if not len(alerts):
    print('OK: No alerts')
    exit(0)
else:
    out_msg = 'WARNING: '
    for alert in alerts:
        out_msg += '{key} is {value} ({default}) | '.format(
            key=alert[0],
            value=alert[1],
            default=alert[2]
        )

    print(out_msg)
    exit(1)
