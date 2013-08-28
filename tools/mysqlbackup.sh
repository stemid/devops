#!/bin/bash
# * Kundnamn, som används i destinationskatalogens namn
# * Databasens namn
# * Databasens användare
# * Användarens lösenord
# Behöver följande PATH i crontab
# PATH=$PATH:/usr/local/sbin:/usr/bin:/bin

customerName=""
mysqlUser=""
mysqlPass=""
mysqlDB=""
mysqlHost=""

# Compress dumps
gzip=1

# Är mysqlDB tom, dumpa alla databaser
mysqlDB=${mysqlDB:-"--all-databases"}

# Syntaxet av date(1) kommandot skiljer sig 
# från Mac OS och BSD. 
backupsDir="/var/backups/mysql/${customerName}"
todayString=$(date -d today +%Y%m%d)
todayStamp=$(date -d today +%s)
weekAgoStamp=$(date -d 'week ago' +%s)

dumpCmd="mysqldump --no-defaults --skip-lock-tables"

if [ -n "$mysqlHost" ]; then
  dumpCmd+=" -h $mysqlHost"
fi

dumpCmd+=" -u $mysqlUser -p$mysqlPass"

# Skapa backup-katalogen om den inte existerar. 
if [[ ! -d "$backupsDir" ]]; then
  echo "Creating directory: $backupsDir"
  mkdir -p "$backupsDir" || exit 1
fi

# Rensa gamla SQL dumpar
for sqlDump in "$backupsDir"/${mysqlDB}-*.sql; do
  # Syntaxet av stat(1) kommandot skiljer sig 
  # på BSD och Mac OS Unix till exempel. 
  if [[ $(stat -c %Z "$sqlDump" >/dev/null 2>&1) -lt "$weekAgoStamp" ]]; then
    rm -f "$sqlDump" || exit 1
  fi
done

todaysMysqlDump="$backupsDir/${mysqlDB}-${todayString}.sql"

# Avsluta om dagens backup redan existerar. 
if [[ -f "$todaysMysqlDump" ]]; then
  echo "Todays dump already exists, exiting" && exit 1
fi

# Skapa ny SQL dump
$dumpCmd "$mysqlDB" > "$todaysMysqlDump" || exit 1

if [ $gzip -eq 1 ]; then
  gzip -f "$todaysMysqlDump" && exit 0
fi
