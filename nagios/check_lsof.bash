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
#
# Version 0.2
#   Now has munin support.

Program_Version='check_lsof.bash 0.2 by Stefan Midjich'

PATH=/bin:/usr/sbin:/usr/bin

# Nagios status codes
OK=0
WARNING=1
CRITICAL=2
UNKNOWN=3

# Get munin service name from $0
get_service() {
  IFS='_' read -ra comp <<< "$0"
  service="${comp[${#comp[@]} -1]}"
  return $service
}

print_usage() {
  cat <<EOF
  Usage: $0 [-V] [-h] [-w <#:#>] [-c <#:#>] <TCP:port>

    -h          Show this help text.
    -V          Show version.
    -w #        Warning threshold.
    -c #        Critical threshold.
    <TCP:port>  TCP port name to check connections on.
                Can also be UDP:port, like TCP:22 or UDP:123. 
                Specify ipv4 or ipv6 like this 4UDP:123.

    Example:
      check_lsof.bash -w 5:680 -c 0:700 4TCP:mysql
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
      # Split argument by : into an array
      warning_array=(${2//:/ })
      warning_threshold_min="${warning_array[0]}"
      warning_threshold_max="${warning_array[1]}"
      shift 2
      ;;
    -c|--critical)
      critical_array=(${2//:/ })
      critical_threshold_min="${warning_array[0]}"
      critical_threshold_max="${warning_array[1]}"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    # TODO: Instead take the remaining arguments and use them as lsof arguments
    #-*)
    #  echo "UNKNOWN: Unknown option (ignored): $1" >&2
    #  shift
    #  ;;
    #*)
    #  break
    #  ;;
  esac
done

# Check final positional argument only if not invoked by munin
if [ -z "$1" -a -z "$MUNIN_PLUGSTATE" ]; then
  print_usage
  exit $UNKNOWN
fi

# Check for munin invocation in final parameter
if [ "$1" -eq 'config' -a -n $MUNIN_PLUGSTATE ]; then
  munin_service=$(get_service $0)
  echo "host_name $FQDN"
  echo "graph_title Number of connections $munin_service"
  echo "graph_category processes"
  echo "graph_vlabel connections"
  echo "connections.label current"
  exit 0
fi

tcp_port=$1

# Get number of open connections
open_connections=$(sudo lsof -t $@ -i "$tcp_port" 2>/dev/null)
lsof_rc=$?

# Check lsof return code status
if [ "$lsof_rc" -ne 0 -a -z "$MUNIN_PLUGSTATE" ]; then
  echo "CRITICAL: No connections for $tcp_port"
  exit $CRITICAL
fi

connection_count=0
# Count lines in output
while IFS= read -r line; do
  ((connection_count++))
done <<<"$open_connections"

if [ -n "$MUNIN_PLUGSTATE" ]; then
  echo "connections.value $open_connections"
  exit $OK
fi

# Check thresholds
if [ $connection_count -lt $critical_threshold_min ]; then
  echo "CRITICAL: Connection count for $tcp_port is $connection_count < $critical_threshold_min"
  exit $CRITICAL
fi

if [ $connection_count -gt $critical_threshold_max ]; then
  echo "CRITICAL: Connection count for $tcp_port is $connection_count > $critical_threshold_max"
  exit $CRITICAL
fi

if [ $connection_count -lt $warning_threshold_min ]; then
  echo "WARNING: Connection count for $tcp_port is $connection_count < $warning_threshold_min"
  exit $WARNING
fi

if [ $connection_count -gt $warning_threshold_max ]; then
  echo "WARNING: Connection count for $tcp_port is $connection_count > $warning_threshold_max"
  exit $WARNING
fi

echo "OK: Connection count for $tcp_port is $connection_count"
exit $OK
