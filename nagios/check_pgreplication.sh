#!/bin/bash
# Does the job for one particular client. Plenty of room for improvement. 
# To be run on master using nrpe
# By Stefan Midjich

# Add the PATH where psql is, this one is for postgresql 9.1 on Debian 6. 
PATH=$PATH:/usr/lib/postgresql/9.1/bin

# Standard nagios exit codes
ST_OK=0
ST_WR=1
ST_CR=2
ST_UK=3

print_usage() {
	echo "Usage: $0 -H <PGHost> -U <PGUser> -D <PGDatabase> -S <PGStandbyHost> [-h] [-t <timeoutSeconds>]"
}

# At least 8 arguments expected
if [ $# -lt 8 ]; then
	print_usage
	exit $ST_UK
fi

# Default timeout value
timeout=5

# TODO: Have multiple -Sn arguments for more standby servers and a loop to check them. 
while test -n "$1"; do
    case "$1" in
	--help)
		print_usage
		shift
		exit $ST_OK
		;;
	-h)
		print_usage
		shift
		exit $ST_OK
		;;
	-H)
		pgMasterServer=$2
		shift 2
		;;
	-S)
		pgStandbyServer=$2
		shift 2
		;;
	-U)
	    pgUserName=$2
	    shift 2
	    ;;
	-D)
	    pgDatabase=$2
	    shift 2
	    ;;
	-T)
	    timeout=$2
	    shift 2
	    ;;
	*)
		shift
		break
		;;
	esac
done

currentTimestamp=$(date +%s)
export PGHOSTADDRESS="$pgMasterServer"
export PGUSER="$pgUserName"
export PGDATABASE="$pgDatabase"

# Check if there is a timestamp already, if there is then UPDATE, if not then INSERT
rows=$(psql -h "$PGHOSTADDRESS" -R, -A -w -q -c "SELECT timestamp FROM replication_testing;" | cut -d, -f2 | tr -d '()')

test "$rows" = "0 rows" && \
	psql -h "$PGHOSTADDRESS" -w -q -c "INSERT INTO replication_testing (timestamp) VALUES ($currentTimestamp)" || \
		psql -h "$PGHOSTADDRESS" -w -q -c "UPDATE replication_testing SET timestamp=$currentTimestamp;"

# Wait n seconds to allow for slow replication. 
# Most of the times the replication is instant between the two servers I tested but it might not always be that way. 
sleep $timeout

# Fetch from standby server and compare
export PGHOSTADDRESS="$pgStandbyServer"
returnedTimestamp=$(psql -h "$PGHOSTADDRESS" -A -R, -w -q -c "SELECT timestamp FROM replication_testing;"|cut -d, -f2)

# Return exit codes
if [[ "$returnedTimestamp" = "$currentTimestamp" ]]; then
	echo "Replication state OK - Replication data returned from standby matched data inserted into master."
	exit $ST_OK
else
	echo "Replication state WARNING - Replication data returned from standby did not match data inserted into master."
	exit $ST_WR
fi

echo "Replication state UNKNOWN - Incorrect use of script?"
exit $ST_UK
