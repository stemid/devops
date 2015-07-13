#!/usr/bin/env bash
# Nagios monitoring script for elasticsearch indices, checking status of 
# indices primarily. 
# Set the warning and critical threshold to a color, so setting both -w
# and -c to red would avoid yellow when you have a single node cluster. 
#
# by Stefan Midjich <swehack@gmail.com>

Program_Version='check_es_indice.bash 0.1 by Stefan Midjich'

# Where is curl on your system?
PATH=/bin:/usr/sbin:/usr/bin

# Nagios status codes
OK=0
WARNING=1
CRITICAL=2
UNKNOWN=3

# Defaults
warning_threshold='yellow'
critical_threshold='red'

print_usage() {
  cat <<EOF
  USAGE: $0 [-h] [-R] <elasticsearch URL>

  -h      Show this help text.
  -R      Set red warning threshold (default is yellow)

  Example:
    $0 -U http://10.4.5.6:9200/_cat/indices
EOF
}

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
      warning_threshold="$2"
      shift 2
      ;;
    -c|--critical)
      critical_threshold="$2"
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

es_url=$1

if [ -z "$es_url" ]; then
  print_usage
  exit $UNKNOWN
fi

indices=$(curl -s "$es_url")
curl_rc=$?

if [ $curl_rc -ne 0 ]; then
  echo "UNKNOWN: No data from ES"
  exit $UNKNOWN
fi

warning_count=0
critical_count=0
while IFS=' ' read -ra line; do
  if [ "${line[0]}" = "$warning_threshold" ]; then
    ((warning_count++))
  fi
  if [ "${line[0]}" = "$critical_threshold" ]; then
    ((critical_count++))
  fi
done <<<"$indices"

if [ $critical_count -gt 0 ]; then
  echo "CRITICAL: $critical_count indices are $critical_threshold"
  exit $CRITICAL
fi

if [ $warning_count -gt 0 ]; then
  echo "WARNING: $warning_count indices are $warning_threshold"
  exit $WARNING
fi

echo "OK: All indices are fine"
exit $OK
