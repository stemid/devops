#!/bin/bash
# Check owner and group of a file. 
# This script depends at least on /usr/bin/stat, or /usr/bin/sudo.
# 
# The -s argument requires /etc/sudoers.d/nagios configuration like this.
# Defaults:nrpe !requiretty
# nrpe ALL=NOPASSWD: /usr/bin/stat
# 
# Or like this if the nagios user runs nrpe
# Defaults:nagios !requiretty
# nagios ALL=NOPASSWD: /usr/bin/stat
# 
# NRPE needs requiretty disabled.

PATH=/bin:/usr/bin

Program_Version='check_owner.bash 0.1 by Stefan Midjich'

# Nagios status codes
OK=0
WARNING=1
CRITICAL=2
UNKNOWN=3

print_usage() {
  cat <<EOF
  Usage: $0 [-V] [-h] [-u <username>] [-g <groupname>] <filename>

    -h              Show this help text.
    -V              Show version.
    -u <username>   Username to check for.
    -g <groupname>  Group to check for.
    -s              Try to use sudo to check, this requires 
                    configuration in sudoers for the nrpe/nagios user. 
    <filename>      File to check owner of.
EOF
}

check_user=''
check_group=''
sudo=''

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
    -u|--user)
      check_user=$2
      shift 2
      ;;
    -g|--group)
      check_group=$2
      shift 2
      ;;
    -s|--sudo)
      sudo='sudo '
      shift
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

# Use last argument as filename
check_filename=$1

# Check owner of filename
file_owner=$($sudo stat -c %U "$check_filename" 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "UNKNOWN: Could not stat file, perhaps use sudo?"
  exit $UNKNOWN
fi

if [[ "$check_owner" && "$check_owner" != "$file_owner" ]]; then
  echo "CRITICAL: Owner does not match on file $check_filename"
  exit $CRITICAL
fi

# Check group of filename
file_group=$($sudo stat -c %G "$check_filename" 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "UNKNOWN: Could not stat file, perhaps use sudo?"
  exit $UNKNOWN
fi

if [[ -n "$check_group" && "$check_group" != "$file_group" ]]; then
  echo "CRITICAL: Group does not match on file $check_filename"
  exit $CRITICAL
fi

echo "OK: Owner matches on file $check_filename"
exit $OK
