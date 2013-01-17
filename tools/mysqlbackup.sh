#!/bin/bash
# Fyll i konfigurationsalternativen här nedan med;
# * Kundnamn, som används i destinationskatalogens namn
# * Databasens namn
# * Databasens användare
# * Användarens lösenord

customerName="kundnamn"
mysqlDB="databasnamn"
mysqlUser="användarnamn"
mysqlPass="lösenord"

# Syntaxet av date(1) kommandot skiljer sig 
# från Mac OS och BSD. 
backupsDir="/var/backups/${customerName}"
todayString=$(date -d today +%Y%m%d)
todayStamp=$(date -d today +%s)
weekAgoStamp=$(date -d 'week ago' +%s)
verbose=0

# Skapa backup-katalogen om den inte existerar. 
if [ ! -d "${backupsDir}" ]; then
	test $verbose -eq 1 && echo "Creating directory: ${backupsDir}"
	mkdir -p "${backupsDir}" || exit 1
fi

# Rensa gamla SQL dumpar
for sqlDump in "${backupsDir}"/${mysqlDB}-*.sql; do
	# Syntaxet av stat(1) kommandot skiljer sig 
	# på BSD och Mac OS Unix till exempel. 
	if [ $(stat -c %Z "${sqlDump}") -lt ${weekAgoStamp} ]; then
		rm -f ${sqlDump} || exit 1
	fi
done

todaysMysqlDump="${backupsDir}/${mysqlDB}-${todayString}.sql"

# Avsluta om dagens backup redan existerar. 
if [ -f "${todaysMysqlDump}" ]; then
	echo "Todays dump already exists, exiting" 1>&2 && exit 1
fi

# Skapa ny SQL dump
mysqldump -u"${mysqlUser}" -p"${mysqlPass}" "${mysqlDB}" > "${todaysMysqlDump}" || exit 1
