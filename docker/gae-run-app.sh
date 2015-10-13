#!/usr/bin/env bash

PORT=8000
HOST_PORT=8001
API_PORT=49532

IP_ADDR=`ifconfig eth0 | grep -o "addr:[0-9][0-9][0-9]\.[0-9]*\.[0-9]*\.[0-9]*" | awk -F ":" '{print $2}'`

cd ${PERSONFINDER_DIR}
echo "Starting Person Finder server"
tools/gae run app --host ${IP_ADDR} --port ${PORT} --admin_host=${IP_ADDR} --admin_port=${HOST_PORT} --api_host=${IP_ADDR} --api_port=${API_PORT}
echo "Person Finder server stopped"
