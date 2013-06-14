#!/bin/bash
# * Kundnamn, som används i destinationskatalogens namn
# * Databasens namn
# * Databasens användare
# * Användarens lösenord

customerName=""
mysqlUser=""
mysqlPass=""
mysqlDB=""
mysqlHost=""

# Compress dumps
gzip=1

# Syntaxet av date(1) kommandot skiljer sig 
# från Mac OS och BSD. 
backupsDir="/var/db/backups/${customerName}"
todayString=$(date -d today +%Y%m%d)
todayStamp=$(date -d today +%s)
weekAgoStamp=$(date -d 'week ago' +%s)

dumpCmd="mysqldump"

if [ -n "$mysqlHost" ]; then
  dumpCmd+=" -h$mysqlHost"
fi

dumpCmd+=" -u'${mysqlUser}' -p'${mysqlPass}'"
if [ -z "$mysqlDB" ]; then
  dumpCmd+=' --all-databases'
fi

mysqlDB=${mysqlDB:-"all-databases"}

# Skapa backup-katalogen om den inte existerar. 
if [[ ! -d "${backupsDir}" ]]; then
  echo "Creating directory: ${backupsDir}"
  mkdir -p "${backupsDir}" || exit 1
fi

# Rensa gamla SQL dumpar
for sqlDump in "${backupsDir}"/${mysqlDB}-*.sql; do
  # Syntaxet av stat(1) kommandot skiljer sig 
  # på BSD och Mac OS Unix till exempel. 
  if [[ $(stat -c %Z "${sqlDump}" >/dev/null 2>&1) -lt ${weekAgoStamp} ]]; then
    rm -f ${sqlDump} || exit 1
  fi
done

todaysMysqlDump="${backupsDir}/${mysqlDB}-${todayString}.sql"

# Avsluta om dagens backup redan existerar. 
if [[ -f "${todaysMysqlDump}" ]]; then
  echo "Todays dump already exists, exiting" && exit 1
fi

# Skapa ny SQL dump
$dumpCmd "${mysqlDB}" > "${todaysMysqlDump}" || exit 1

if [ $gzip -eq 1 ]; then
  gzip "${todaysMysqlDump}" && exit 0
fi

