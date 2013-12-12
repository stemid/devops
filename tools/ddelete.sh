#!/usr/bin/env bash
# vim: set ts=2
# Delete file based on its age
# Be careful, here's an example:
# ddelete.sh -d '1 year ago' file.txt
# ddelete.sh otherfile.xls
# Default is '1 month old'
#
# OBSERVE ###
# This requires GNU stat and GNU date to work properly. 
#
# By Stefan Midjich

# Default last modified date for files
modifiedDate=$(date -d '1 month ago' +'%s')
maxModifiedDate=$(date -d 'now' +'%s')
onlyPrint=0
verbose=0

print_usage() {
  cat << 'EOF' 1>&2
    Usage: $0 [-hvp] [-d <last modified date>] [-m <max modified date>] <filename>...

      -h  Show this help text.

      -p  Only print matching files, don't delete anything. 

      -d  Last modified date in this form: '1 day ago'
          or '1 month ago'. See date(1) for more examples. 

      -m  Maximum modified date, the last modified date to delete. 
          Takes the same form as -d argument. 

      -v  Be verbose.

      <filename> is a list of filenames to delete.

      Example: find /var/www -type f | xargs $0 -d '1 month ago' -m '1 hour ago'
      Example 2: $0 -d '1 week ago' old_dump.sql
EOF
}

# No arguments?
if [ $# -lt 1 ]; then
	print_usage
  exit 1
fi

# Traverse arguments with getopts
while getopts 'pvm:d:' opt; do
  case "$opt" in
    p)
      onlyPrint=1
      ;;
    d)
      modifiedDate=$(date -d "$OPTARG" +'%s')
      ;;
    m)
      maxModifiedDate=$(date -d "$OPTARG" +'%s')
      ;;
    v)
      verbose=1
      ;;
    ?)
      print_usage
      exit 1
    ;;
  esac
done

# Check if there are any positional arguments left. 
if [ $(( $# - $OPTIND )) -lt 1 ]; then
  echo "No filename specified" 1>&2
  print_usage
  exit 1
fi

# Shift the internal arguments list to the remaining arguments.
shift $OPTIND

# Traverse the remaining positional arguments as filenames.
for filename do
  # Skip if the file does not exist.
  if [ ! -e "$filename" ]; then
    echo "File does not exist, skipping..." 1>&2
    continue
  fi

  # Take stat info from the file.
  read -a statData <<<$(stat -t "$filename" || exit 1)
  fileModifiedDate=${statData[12]}

  # Check the file info last modified date and compare with provided arguments. 
  if [ "$modifiedDate" -gt "$fileModifiedDate" -a "$maxModifiedDate" -lt "$fileModifiedDate" ]; then
    test $onlyPrint = 1 && echo "$filename: $fileModifiedDate" && exit 0
    rm -rf "$filename" && test $verbose = 1 && echo "$filename with change time $(date -d @"$fileModifiedDate") deleted"
    exit 0
  else
    test $verbose = 1 && echo "$filename with change time $(date -d @"$fileModifiedDate") skipped"
  fi
done

exit 0
