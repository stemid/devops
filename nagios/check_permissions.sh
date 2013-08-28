#!/bin/bash

EXIT_OK=0
EXIT_WARNING=1
EXIT_CRITICAL=2
EXIT_UNKNOWN=3

check_filename=$1
check_permissions=$2

if [[ -z "$check_filename" || -z "$check_permissions" ]]; then
  echo "Usage: ./$0 <filename> <permissions>" 2>&1
  exit $EXIT_UNKNOWN
fi

if [ ! -e "$check_filename" ]; then
  echo "UNKNOWN: File is not readable or not found."
  exit $EXIT_UNKNOWN
fi

octal_permissions=$(stat -c '%a' "$check_filename")

if [ "$octal_permissions" != "$check_permissions" ]; then
  echo "WARNING: Incorrect permissions $octal_permissions: $check_filename"
  exit $EXIT_WARNING
else
  echo "OK: Permissions are correct $octal_permissions: $check_filename"
  exit $EXIT_OK
fi
