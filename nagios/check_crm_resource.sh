#!/bin/bash
# Check resource status in pacemaker.
# Should be run with sudo -u nagios in nrpe_local.conf.
# With the following in /etc/sudoers.d/nagios and mode 0440. 
#  Cmnd_Alias	CRM_MON = /usr/sbin/crm_mon
#  nagios	ALL=NOPASSWD: CRM_MON

# TODO: Finish tomorrow, getting late... =|

usage() {
	cat <<USAGE
$0 -w <range> -c <range> [-r <rsc>]

Options:
	-h 
		This help text.

	-w <range>
		Warning threshold in min:max format. 
	
	-c <range>
		Critical threshold in min:max format.

Filters:
	-r <rsc>
		Resource ID in crmsh.

RANGEs are specified 'min:max' or 'min:' or ':max' (or 'max'). If
specified 'max:min', a warning status will be generated if the
count is inside the specified range

FILTERs can be anything that matches one or more resources. 
USAGE
}

# Nagios return codes
OK=0
WARNING=1
CRITICAL=2
UNKNOWN=3

# Regex patterns
shopt -s nocasematch
RangePattern='([[:digit:]]*):([[:digit:]]*)'
defaultFilterPattern='([[:alpha:]]+): \
	([[:digit:]]+) node[s]? online, ([[:digit:]]+) resources configured'
nodesPattern='^([[:digit:]]+) Node[s]? configured, ([[:digit:]]+) expected vote[s]?$'
resPattern='^([[:digit:]]+) Resource[s]? configured\.$'
nodePattern='^'

if ! which crm_mon; then
	echo 'UNKNOWN: Must have crm_mon in $PATH for nagios' 1>&2 && exit $UNKNOWN
fi

# Read cli arguments
while [ -n "$1" ]; do
	case "$1" in
		-h)
			usage 1>&2 && exit $OK
			shift
			break
			;;
		-w)
			if [[ "$2" =~ $RangePattern ]]; then
				warningMin=${BASH_REMATCH[1]:-0}
				warningMax=${BASH_REMATCH[2]}
			else
				echo "UNKNOWN: Incorrect range argument" && exit $UNKNOWN
			fi
			shift 2
			;;
		-c)
			if [[ "$2" =~ $RangePattern ]]; then
				criticalMin=${BASH_REMATCH[1]:-0}
				criticalMax=${BASH_REMATCH[2]}
			else
				echo "UNKNOWN: Incorrect range argument" 1>&2 && exit $UNKNOWN
			fi
			shift 2
			;;
		-r)
			if [ -n "$2" ]; then
				resFilter="$1"
				resPattern=${2/#-}

			else
				echo "UNKNOWN: Filter requires an argument" 1>&2 && exit $UNKNOWN
			fi
			shift 2
			;;
		*)
			shift
			break
			;;
	esac
done

if [[ "$resPattern" == 'r' ]] # Normal resource filter
	while IFS= read -r crmOut; do
		if [[ "$crmOut" =~ $nodesPattern
	done <<<$(crm_mon -1nNQ)
else if [[ $(crm_mon -s) =~ $defaultFilterPattern ]]; then
	crmStatus=${BASH_REMATCH[1]:-'Unknown'}
	totalNodes=${BASH_REMATCH[2]:-0}
	totalServices=${BASH_REMATCH[3]:-0}
	if [[ $crmStatus != 'Ok' ]]; then
		OutputText='WARNING: '
	fi
else
	echo "UNKNOWN: Failed to parse output" && exit $UNKNOWN
fi
