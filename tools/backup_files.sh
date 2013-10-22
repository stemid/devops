#!/bin/bash
# General backup script just to tar and zip files or directories. 
# By Stefan Midjich

## Set this ##
backup_customer=''
## Set this ##

# Don't touch anything else, unless you're a nerd. 
if [ ${#1} -eq 0 ]; then
  echo "Usage: $0 <backup file/directory>"
  exit 2
fi

backup_title=$(basename "$1")
backup_path="/var/backups/$backup_customer"
backup_filename="$backup_path/$backup_title-$(date -d today +%Y%m%d).tar.bz2"
today_stamp=$(date -d today +%s)
week_ago_stamp=$(date -d 'week ago' +%s)

test -d "$backup_path/$backup_customer" || mkdir -p "$backup_path"

# Start backup
test -f "$backup_filename" || tar -cjvf "$backup_filename" "$1" || exit $?

# Purge old backups
for file in "$backup_path/$backup_title"-*; do
  # Linux only stat syntax, BSD and Mac OS are stat -t '%s' -f '%c' "$file"
  test "$(stat -c '%Z' '$file' 2>/dev/null)" -lt "$week_ago_stamp" && rm -f "$file" || exit $?
done
