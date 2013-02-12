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
# create table replication_test (
#  "lastcheck" timestamp not null default current_timestamp on update current_timestamp
# );

# Mysql should listen on all interfaces
mysqlHost=127.0.0.1
mysqlPort=3306
mysqlUser=root
mysqlPass=password
mysqlDB=nagios_test
mysqlTable=replication_test
mysqlSlave=10.0.0.1

timeout=30
sleepTimeout=5

# Nagios exit codes
ST_OK=0
ST_WR=1
ST_CR=2
ST_UK=3

print_usage() {
	echo "Usage: $0 -H <MySQLHost> -U <MySQLUser> -P <MySQLPassword> -p <MySQLPort> -D <MySQLDB> -S <MySQLSlave> [-h]" 1>&2
}

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

mysqlArgs="-sNB --connect_timeout=$timeout -u$mysqlUser -p$mysqlPass -D$mysqlDB"

# Update or create the current timestamp
oldDBTimestamp=$(mysql -h"$mysqlHost" $mysqlArgs -e "select unix_timestamp(lastcheck) from $mysqlTable;" >/dev/null 2>&1)

if [ $? -ne 0 ]; then
	echo "Critical: Could not connect to database"
	exit $ST_CR
fi

test -z "$oldDBTimestamp" && mysql -h"$mysqlHost" $mysqlArgs -e "insert into $mysqlTable (lastcheck) values (null);" || \
	mysql -h"$mysqlHost" $mysqlArgs -e "update $mysqlTable set (lastcheck=null);"

newDBTimestamp=$(mysql -h"$mysqlHost" $mysqlArgs -e "select unix_timestamp(lastcheck) from $mysqlTable;")

# Wait for slow replication
sleep $sleepTimeout

slaveDBTimestamp=$(mysql -h"$mysqlHost" $mysqlArgs -e "select unix_timestamp(lastcheck) from $mysqlTable;")

if [ "$newDBTimestamp" = "$slaveDBTimestamp" ]; then
	echo "Replication state OK - Replication data returned from standby matched data entered into master."
	exit $ST_OK
else
	echo "Replication state WARNING - Replication data returned from standby did not match data inserted into master."
	exit $ST_WR
fi

echo "Replication state UNKNOWN - Incorrect use of script?"
exit $ST_UK
