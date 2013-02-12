#!/bin/bash
# NTLM Authentication check 
# Requires curl binary compiled with SSL and NTLM 
# support, located in $PATH.  
# By Stefan.Midjich

headerFile=$(mktemp "/tmp/$0.XXX")
antiDebug='-o /dev/null'
timeout='-m 10'
useSSL=''
okCode=200

usage() {
	cat <<EOD
	Usage: $0 -U <target URL> -u <username> -P <password>

	Authenticates at the URL given using Microsoft NTLM and returns OK (0) 
	status if 200 is found in return header. This return code can be modified
	with -c argument. 

	-h
		This help text.
	-U 
		Target URL, including http or https. Just as in your browser. 
	-u
		NTLM username. 
	-P
		NTLM password. 
	-C
		HTTP return code to signal OK status. 
	-c
		Critical timeout, this script does not make use of warning timeout. 
	-ssl
		Make use of SSL, which is often the default with NTLM. 
	-d
		Debug output. 
EOD
}

while [ -n "$1" ]; do
	case "$1" in
	--help)
		usage
		shift
		;;
	-h)
		usage
		shift
		;;
	-U)
		targetURL=$2
		shift 2
		;;
	-u)
		username=$2
		shift 2
		;;
	-P)
		password=$2
		shift 2
		;;
	-C)
		okCode=$2
		shift 2
		;;
	-c)
		timeout="-m $2"
		shift 2
		;;
	-ssl)
		useSSL='-ssl'
		shift
		;;
	-d)
		antiDebug=''
		shift
		;;
	*)
		shift
		break
		;;
	esac
done

if [[ -z "$targetURL" || -z "$username" || -z "$password" ]]; then
	usage 1>&2
	rm -f "$headerFile"
	exit 2
fi

curl $antiDebug $useSSL $timeout -sS --ntlm -D $headerFile -u $username:$password $targetURL
returnVal=$?

if [ $returnVal -ne 0 ]; then
	echo "NTLM: curl exited with error: $returnVal" 1>&2
	exit 2
fi

if grep -w "$okCode" $headerFile >/dev/null; then
	echo "NTLM: Authentication succeeded"
	rm -f "$headerFile"
	exit 0
else
	echo "NTLM: Authentication failed"
	rm -f "$headerFile"
	exit 2
fi
