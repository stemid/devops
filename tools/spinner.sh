#!/usr/bin/env bash
# Example of a spinner for bash that can be used for entertainment during
# long running processes. Works only on Linux.
# Stefan Midjich <swehack@gmail.com> 2016

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

# # Use like this for example, to make a command you can call other commands
# # with and get a spinner until they finish.
# source spinner.sh
#
# exec "$@" &
# pid=$!
#
# spinner $pid 0.2
#
# echo
# echo "Process[$pid] $@ done"
