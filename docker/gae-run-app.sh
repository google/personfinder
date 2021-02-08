#!/usr/bin/env bash

PORT=8000
HOST_PORT=8001
API_PORT=49532

IP_ADDR=`ip addr list eth0 | grep 'inet ' | cut -d' ' -f6 | cut -d'/' -f1`

cd ${PERSONFINDER_DIR}
echo "Starting Person Finder server"
dev_appserver.py app --host ${IP_ADDR} --port ${PORT} --admin_host=${IP_ADDR} --admin_port=${HOST_PORT} --api_host=${IP_ADDR} --api_port=${API_PORT} --skip_sdk_update_check
echo "Person Finder server stopped"
