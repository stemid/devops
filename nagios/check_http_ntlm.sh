#!/bin/bash
# HTTP auth check for nagios, using curl for NTLM and SSL support.
# Requires curl binary compiled with SSL and NTLM
# support, located in $PATH.  
# Warning: Places temporary files on /tmp with header and body contents.
#
# By Stefan Midjich <swehack at gmail.com>

# Initialize some default values and temporary files.
umask 077
headerFile=$(mktemp "/tmp/$(basename $0).headerXXX")
contentFile=$(mktemp "/tmp/$(basename $0).contentXXX")
outputBody='-o /dev/null'
outputHeader="-D $headerFile"
timeout='-m 10'
useNTLM=''
useSSL=''
okCode=200
searchString=''
followRedirect='-L --max-redirs 5'

# A couple of helper functions.
clean_up() {
  #test -f "$headerFile" && rm -f "$headerFile"
  #test -f "$contentFile" && rm -f "$contentFile"
  return
}

usage() {
	cat <<EOD
Usage: $0 -U <target URL> -u <username> -P <password>

Authenticates at the URL given using Microsoft NTLM and returns OK (0) 
status if 200 is found in return header. This return code can be modified
with -c argument. 

  -h
    This help text.
  -U <url>
    Target URL, including http or https. Just as in your browser. 
  -u <username>
    Basic AUTH username
  -P <password>
    Basic AUTH password
  -N
    Use NTLM, by default only use basic auth.
  --ntlm-username <username>
    NTLM username. 
  --ntlm-password <password>
    NTLM password. 
  -C <return code>
    HTTP return code to signal OK status. 
  -S <string>
    String to look for in response body, this overrides -C.
  -c <timeout>
    Critical timeout, this script does not make use of warning timeout. 
  --ssl
    Make use of SSL, which is often the default with NTLM. 
  -R
    Do not follow redirects, default is to follow 5 redirects.
  -d
    Debug output. 
EOD
}

# Run cleanup function at exit
trap clean_up EXIT

# Process command line arguments the old school way, without getopt.
while [ -n "$1" ]; do
	case "$1" in
	--help)
		usage
    exit 0
		shift
		;;
	-h)
		usage
    exit 0
		shift
		;;
	-U)
		targetURL="$2"
		shift 2
		;;
  -N)
    useNTLM='--ntlm'
    shift
    ;;
	--ntlm-username|-u)
		username="$2"
		shift 2
		;;
	--ntlm-password|-P)
		password="$2"
		shift 2
		;;
	-C)
		okCode=$2
		shift 2
		;;
  -S)
    searchString="$2"
    outputBody="-o $contentFile"
    shift 2
    ;;
	-c)
		timeout="-m $2"
		shift 2
		;;
	--ssl)
		useSSL='-ssl'
		shift
		;;
  -R)
    followRedirect=''
    shift
    ;;
	-d)
		debug='-v'
		shift
		;;
	*)
		shift
		break
		;;
	esac
done

# Verify bare minimum of CLI arguments.
if [[ -z "$targetURL" ]]; then
	usage 1>&2
	exit 2
fi

curl $debug $followRedirect $useSSL $timeout -sS $useNTLM $outputHeader $outputBody -u "$username:$password" "$targetURL"
returnVal=$?

if [ $returnVal -ne 0 ]; then
	echo "UNKNOWN: curl exited with error: $returnVal"
	exit 3
fi

# If a searchString is specified, search for its first occurance in the file
# with the curl response body contents.
if [ -n "$searchString" ]; then
  if grep -q "$searchString" $contentFile 2>/dev/null; then
    echo "OK: Found string '$searchString'"
    exit 0
  else
    echo "CRITICAL: Could not find string '$searchString'"
    exit 2
  fi
fi

# Poorly search for the HTTP OK code specified in the headers. This could be
# vastly improved but works for my use cases.
if grep -wq "$okCode" $headerFile 2>/dev/null; then
	echo "OK: HTTP request succeeded"
	exit 0
else
	echo "CRITICAL: HTTP request failed"
	exit 2
fi
