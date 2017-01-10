#!/usr/bin/env bash

echo "[+] --> Installing dependencies"
pip install -b app/lib --requirement requirements.txt
echo "[+] --> Dependencies installed"

for f in $(find app/lib/ -maxdepth 1 -type d); do
	
	touch $PWD/$f/__init__.py
done


