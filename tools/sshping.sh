#!/bin/bash
# "Ping" a hosts ssh port by repeatedly connecting to it using netcat. Useful
# when waiting for a system to reboot so you can login to it. Could probably
# be replaced by autossh.
# Usage: sshping.sh host [optional port defaults to 22]
# by Stefan Midjich <swehack at gmail.com> 2015

while sleep 0.5; do
  nc -vv -w 1 -z ${1:-localhost} ${2:-22}
done
