#!/usr/bin/env bash
# Prepare a CentOS/Fedora VM for templating.

yum -y update
yum clean all

# Remove SSH host keys, they will re-generate at boot.
find /etc/ssh/*host* |xargs rm -f
find /root/.ssh/ -type f |xargs rm -f
find /home/*/.ssh/ -type f |xargs rm -f

# Replace UUIDs with actual devices in /etc/fstab
while IFS=$'= \t' read -r -a data; do
    uuid="${data[1]}"
    blkid -U "$uuid" &>/dev/null|| continue
    disk=$(blkid -U "$uuid")
    test -b "$disk" || continue
    sed -i -e "s:^UUID=$uuid:$disk:" /etc/fstab
done < <(grep ^UUID= /etc/fstab)

# Maybe use this solution instead.
<< EOF
for disk_uuid in /dev/disk/by-uuid/*; do
    disk=$(readlink -f "$disk_uuid")
    uuid=${disk_uuid##*/}
    if grep -c "^UUID=$uuid" /etc/fstab &>/dev/null; then
        sed -i -e "s:^UUID=$uuid:$disk:" /etc/fstab
    fi
done
EOF

cat /etc/fstab
echo -n "Review fstab, type yes to continue and no to abort. (yes/no): "
read answer

test "$answer" = 'yes' || exit 1

# Replace UUIDs from network config
sed -i -e '/^UUID=.*/d' /etc/sysconfig/network-scripts/ifcfg-*

# Remove other network specific config from.
sed -i -e '/^IPV6_.*/d' /etc/sysconfig/network-scripts/ifcfg-*
sed -i -e '/^IPADDR=.*/d' /etc/sysconfig/network-scripts/ifcfg-*
sed -i -e '/^PREFIX=.*/d' /etc/sysconfig/network-scripts/ifcfg-*
sed -i -e '/^GATEWAY=.*/d' /etc/sysconfig/network-scripts/ifcfg-*
sed -i -e '/^DOMAIN=.*/d' /etc/sysconfig/network-scripts/ifcfg-*
sed -i -e '/^DNS[0-9]*=.*/d' /etc/sysconfig/network-scripts/ifcfg-*

# Remove known machine specific udev rules.
find /etc/udev/rules.d/ -iname '70*net*' |xargs rm -f

# Prevent ntp from panicing from tinkering
if test -a /etc/ntp.conf && grep -c 'tinker panic 0' /etc/ntp.conf &>/dev/null; do
    sed -i -e '1 i\tinker panic 0\n' /etc/ntp.conf

>/root/.bash_history
>/home/*/.bash_history
>/root/anaconda-ks.cfg

cat /dev/null > /var/log/wtmp

echo -n "Next command (sys-unconfig) will close the ssh connection. Type yes to proceed. (yes/no): "
read answer

test "$answer" = 'yes' || exit 1
sys-unconfig

