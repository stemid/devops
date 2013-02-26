#!/usr/bin/env bash
# vim: set ts=2
# Delete file based on its age
# Be careful, here's an example:
# ddelete.sh -d '1 year ago' file.txt
# ddelete.sh otherfile.xls
# Default is '1 month old'

# Default last modified date for files
modifiedDate=$(date -d '1 month ago' +'%s')
onlyPrint=0

print_usage() {
	echo "Usage: $0 [-d <last modified date>] <filename>" 1>&2
}

if [ $# -lt 1 ]; then
	print_usage
	exit 1
fi

while getopts 'pd:' opt; do
	case $opt in
		p)
			onlyPrint=1
			;;
		d)
			modifiedDate=$(date -d "$OPTARG" +'%s')
			;;
		?)
			print_usage
			exit 1
			;;
	esac
done

shift $((OPTIND-1))

if [ -z "$1" ]; then
	print_usage
	exit 1
fi

filename=$1
fileModifiedDate=$(stat -t "$filename"|cut -d' ' -f13)

if [ $onlyPrint -eq 1 ]; then
	echo "$filename: $fileModifiedDate"
fi

if [ "$modifiedDate" -gt "$fileModifiedDate" ]; then
	rm -rf "$filename"
	exit 0
fi

exit 1
