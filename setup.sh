#!/usr/bin/env bash

echo '[+] --> Installing all dependencies'

command -v pip >/dev/null 2>&1 || { echo "'pip' is not installed. Please install it." >&2; exit 1; }

pip install -b app/lib --requirement requirements.txt

if [ -z $? ]; then
	echo '[-]-->  Error during installation'
else
	echo '[+] --> Requirements installed'
fi
