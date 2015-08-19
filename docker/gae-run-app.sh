#!/usr/bin/env bash

PORT=8000
IP_ADDR=`ifconfig eth0 | grep -o "addr:[0-9][0-9][0-9]\.[0-9]*\.[0-9]*\.[0-9]*" | awk -F ":" '{print $2}'`

cd ${PERSONFINDER_DIR}
tools/gae run app --port=${PORT} --host=${IP_ADDR}
