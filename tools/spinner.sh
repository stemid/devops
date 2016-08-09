#!/usr/bin/env bash

spinner() {
  local pid=$1 && shift
  local delay=${1:-1} && shift
  local i=1
  local sp="/-\|"

  echo -n ' '
  # Could be [ lsof -p $pid &>/dev/null ] on Mac OSX perhaps.
  while [ -d /proc/$pid ]; do
    printf "\b${sp:i++%${#sp}:1}"
    sleep $delay
  done
}

exec "$@" &
pid=$!

spinner $pid 0.2

echo
echo "Process[$pid] $@ done"
