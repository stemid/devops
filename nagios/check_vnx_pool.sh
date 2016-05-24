#!/bin/bash
#
# Check the usage of an EMC VNX pool.
#
# Requires that an encrypted security credentials files is located
# somewhere on the system. 
#
# The user credentials file can be created using the following command:
#
# /opt/Navisphere/bin/naviseccli -secfilepath /etc/navisphere -User monitor -Scope 1 -AddUserSecurity
#
# Where the monitor user is a read only user defined in the SAN.
# NOTE: That the user running the command to create the security files 
# must be the user reading them after, any other user will not be able
# to use the files. So for example nagios user would need to do this.
#
# sudo -u nagios /opt/Navisphere/bin/naviseccli -secfilepath /etc/navisphere ...
# To create files used by the nagios user.
#
# by Per-Ola Gustafsson
# Modified by Stefan Midjich <swehack@gmail.com>

navsecfilepath=/etc/navisphere
navcli="/opt/Navisphere/bin/naviseccli -secfilepath $navsecfilepath "

# nagios return codes
OK=0
WARNING=1
CRITICAL=2
UNKNOWN=3

#
# Default values for the arguments
#
emc_sp=0
pool_id=0
warning=70.0
critical=85.0


function usage()
{
cat <<EOF
Check the usage of an EMC VNX pool.

	Options:
		<ip>    Specify the ip adress of SPA or SPB.
		<id>    The pool id of the pool to be checked.
		<float> Warning level in percent.
		<float> Critical level in percent.

EOF
}

function float_cond()
{
	# Evaluate a floating point conditional expression.
	# Returns either 1 or 0, depending on if the evaluation
	# true of false.
	# This function can be used in bash if statements.

	local cond=0
	if [ $# -gt 0 ]; then
		cond=$(echo "$*" | bc -q 2>/dev/null)
		if [ -z "$cond" ]; then cond=0; fi
		if [ "$cond" != 0 -a "$cond" != 1 ]; then cond=0; fi
	fi
	local stat=$((cond == 0));
	return $stat;
}


function check_pool()
{
	local pool_usage=$($navcli -h $emc_sp storagepool -list -id $pool_id -prcntFull | awk -F: '{ if ($1 == "Percent Full") { print $2; } }')


  pool_usage="$(echo -e "${pool_usage}" | tr -d '[[:space:]]')"
	if float_cond "$pool_usage < $warning"; then
		echo "OK - $pool_usage % of pool $pool_id is used. | 'usage'=$pool_usage%;$warning;$critical;0;100;"
		exit $OK;

	elif float_cond "($pool_usage >= $warning) && ($pool_usage < $critical)"; then
		echo "WARNING - $pool_usage % of pool $pool_id is used. | 'usage'=$pool_usage%;$warning;$critical;0;100;"
		exit $WARNING;

	elif float_cond "$pool_usage >= $critical"; then
		echo "CRITICAL - $pool_usage % of pool $pool_id is used. | 'usage'=$pool_usage%;$warning;$criticali;0;100;"
		exit $CRITICAL;

	else 
		echo "UNKNOWN - pool usage of $pool_id "
		exit $UNKNOWN;
	fi
}


# Gee this is ugly. But I don't want to spend time to fix it.
if [ $# -eq 2 ]; then
  emc_sp=$1
  pool_id=$2
elif [ $# -eq 4 ]; then 
  emc_sp=$1
  pool_id=$2
  warning=$3
  critical=$4
else
  usage
  exit $UNKOWN
fi

check_pool
