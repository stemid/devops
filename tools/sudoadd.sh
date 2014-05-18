#!/bin/sh
# Add things to sudoers easily while executing them the first time. 
# Only tested on Ubuntu 14.04 so far. 
# by Stefan Midjich <swehack@gmail.com>

username="$(whoami)"
sudoers_file="/etc/sudoers.d/sudoadd_$username"
sudoers_testfile="/tmp/sudoadd_$username.test"
sudoers_data="$username ALL=NOPASSWD:$*"

sudo echo -n "Adding to $sudoers_file: "

# Test it with visudo first
echo "$sudoers_data" | sudo tee "$sudoers_testfile"
sudo visudo -cf "$sudoers_testfile";rc=$?
sudo rm -f "$sudoers_testfile"
test $rc -ne 0 && exit $?

# Add it for real
if sudo grep -s "$sudoers_data" "$sudoers_file" &>/dev/null; then
  echo "$sudoers_data" | sudo tee -a "$sudoers_file" &>/dev/null
fi

# Lastly execute command
sudo $*
