#!/bin/bash
# Nagios script to count number of TCP connections by using lsof. 
# Most other scripts are perl and too complex imo, I just want to check 
# lsof -ni | wc -l for a process. 
# This requires 
#   /bin/bash
#   /usr/sbin/lsof 
#   /usr/bin/sudo
#
# NOTE: Macintosh OS X has no pidof(8) program.
# On FreeBSD you can install sysutils/pidof.
#
# To run this with nrpe you need to setup sudoers like this
# Defaults:nrpe !requiretty
# nrpe ALL=NOPASSWD: /usr/sbin/lsof
# Or like this if the nagios user runs nrpe
# Defaults:nagios !requiretty
# nagios ALL=NOPASSWD: /usr/sbin/lsof
# Place that into /etc/sudoers.d/nrpe and make the file 0440

Program_Version='check_lsof.bash 0.1 by Stefan Midjich'

PATH=/bin:/usr/sbin:/usr/bin

# Nagios status codes
OK=0
WARNING=1
CRITICAL=2
UNKNOWN=3

print_usage() {
  cat <<EOF
  Usage: $0 [-V] [-h] [-w <#>] [-c <#>] <TCP:port>

    -h          Show this help text.
    -V          Show version.
    -w #        Warning threshold.
    -c #        Critical threshold.
    <TCP:port>  TCP port name to check connections on.
                Can also be UDP:port, like TCP:22 or UDP:123. 
                Specify ipv4 or ipv6 like this 4UDP:123.
EOF
}

tcp_port=''
warning_threshold=2
critical_threshold=2

# Parse arguments
while :; do
  case $1 in
    -h|--help|-\?)
      print_usage
      exit $OK
      ;;
    -V|--version)
      echo $Program_Version
      exit $OK
      ;;
    -w|--warning)
      warning_threshold=$2
      shift 2
      ;;
    -c|--critical)
      critical_threshold=$2
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "UNKNOWN: Unknown option (ignored): $1" >&2
      shift
      ;;
    *)
      break
      ;;
  esac
done

# Check final positional argument
if [ -z "$1" ]; then
  print_usage
  exit $UNKNOWN
fi

tcp_port=$1

# Get number of open connections
open_connections=$(sudo lsof -Pni "$tcp_port" 2>/dev/null)
lsof_rc=$?

# Check lsof return code status
if [ "$lsof_rc" -ne 0 ]; then
  echo "CRITICAL: No connections for $tcp_port"
  exit $CRITICAL
fi

connection_count=0
while IFS= read -r line; do
  if [[ "$line" =~ '^COMMAND' ]]; then
    continue
  fi

  ((connection_count++))
done <<<"$open_connections"

if [ $connection_count -lt $critical_threshold ]; then
  echo "CRITICAL: Connection count for $tcp_port is $connection_count"
  exit $CRITICAL
fi

if [ $connection_count -lt $warning_threshold ]; then
  echo "WARNING: Connection count for $tcp_port is $connection_count"
  exit $WARNING
fi

echo "OK: Connection count for $tcp_port is $connection_count"
exit $OK
