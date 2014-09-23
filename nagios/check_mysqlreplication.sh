#!/usr/bin/env bash
# Simple script to check mysql replication. 
# The setup for this is one Nagios host on a VIP shared by 
# both replication nodes but set as Master on the same node
# that is mysql master. 
# Both nodes have nrpe with this script installed, so that 
# means whichever node is master will receive the NRPE 
# request. 
# With this method I ensure that the script always runs 
# by nrpe on the mysql master. 
# 
# create table replicationtest (
#  "lastcheck" timestamp not null default current_timestamp on update current_timestamp
# );

# Set static configuration below
# Mysql must listen on at least one interface
mysqlHost=127.0.0.1
mysqlPort=3306
mysqlUser=root
mysqlPass=password
mysqlDB=nagios_test
mysqlTable=replicationtest
mysqlSlave=10.0.0.1

# Connect timeout, and replication timeout
timeout=30
sleepTimeout=2

# Nagios exit codes
ST_OK=0
ST_WR=1
ST_CR=2
ST_UK=3

print_usage() {
	echo "Usage: $0 -H <MySQLHost> -U <MySQLUser> -P <MySQLPassword> -p <MySQLPort> -D <MySQLDB> -S <MySQLSlave> [-h]" 1>&2
}

# Must have at least 12 arguments
if [ $# -lt 12 ]; then
	print_usage
	exit $ST_UK
fi

# Loop through arguments in a crude way
while test -n "$1"; do
	case "$1" in
		--help)
			print_usage
			exit $ST_UK
			;;
		-H)
			mysqlHost=$2
			shift 2
			;;
		-U)
			mysqlUser=$2
			shift 2
			;;
		-P)
			mysqlPass=$2
			shift 2
			;;
		-p)
			mysqlPort=$2
			shift 2
			;;
		-D)
			mysqlDB=$2
			shift 2
			;;
		-S)
			mysqlSlave=$2
			shift 2
			;;
		-s)
			sleepTimeout=$2
			shift 2
			;;
		-t)
			timeout=$2
			shift 2
			;;
		*)
			shift
			break
			;;
	esac
done

# Build argument string without host arg and SQL command
mysqlArgs="-P$mysqlPort -sNB --connect-timeout=$timeout -u$mysqlUser -p$mysqlPass -D$mysqlDB"

# Check the old timestamp, if any
oldDBTimestamp=$(mysql -h"$mysqlHost" $mysqlArgs -e "select unix_timestamp(lastcheck) from $mysqlTable order by lastcheck desc limit 1;" >/dev/null 2>&1)

# Good opportunity to throw error if connection fails
if [ $? -ne 0 ]; then
	echo "Critical: Could not connect to database"
	exit $ST_CR
fi

# Cleanup code
set -e
function cleanupDB() {
  # Clean up db
  mysql -h"$mysqlHost" $mysqlArgs -e "DELETE FROM $mysqlTable;"
}
trap cleanupDB EXIT

# Create or update the timestamp
test -z "$oldDBTimestamp" && mysql -h"$mysqlHost" $mysqlArgs -e "insert into $mysqlTable (lastcheck) values (null);" || \
	mysql -h"$mysqlHost" $mysqlArgs -e "update $mysqlTable set lastcheck=null;"

# Get the new timestamp
newDBTimestamp=$(mysql -h"$mysqlHost" $mysqlArgs -e "select unix_timestamp(lastcheck) from $mysqlTable;")

# Wait for slow replication
sleep $sleepTimeout

# Get the slave timestamp
slaveDBTimestamp=$(mysql -h"$mysqlSlave" $mysqlArgs -e "select unix_timestamp(lastcheck) from $mysqlTable;")

# Clear the DB
mysql -h"$mysqlHost" $mysqlArgs -e "delete from $mysqlTable;"

# Compare the two
if [ "$newDBTimestamp" = "$slaveDBTimestamp" ]; then
	echo "Replication state OK - Replication data returned from standby matched data entered into master."
	exit $ST_OK
else
	echo "Replication state WARNING - Replication data returned from standby did not match data inserted into master."
	exit $ST_WR
fi

echo "Replication state UNKNOWN - Incorrect use of script?"
exit $ST_UK
