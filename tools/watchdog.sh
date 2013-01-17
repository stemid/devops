#!/bin/bash
# Simple watchdog script
# By Stefan Midjich 2013-01-17
# Use with crontab like this in /etc/cron.d/watchdog for example
# 
# PATH=/sbin
# MAILTO=stefan,root
# */10	*	*	*	*	root /usr/local/bin/watchdog.sh sendmail

test -z "$1" && exit 1

service "$1" status >/dev/null 2>&1
rc=$?

test $rc -ne 0 && echo "$1: Not running" && exit $rc
#test $rc -ne 0 && echo "$1: Not running" && service "$1" start && exit $?

:
