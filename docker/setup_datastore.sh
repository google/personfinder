#!/usr/bin/env bash
# Initialize the Person Finder's datastore the first time it is run on this machine.

PORT=8000
IP_ADDR=`ifconfig eth0 | grep -o "addr:[0-9][0-9][0-9]\.[0-9]*\.[0-9]*\.[0-9]*" | awk -F ":" '{print $2}'`

if [ 0 = ${INIT_DATASTORE} ]; then
    echo "Setting datastore for server at ${IP_ADDR}:${PORT}"
    cd ${PERSONFINDER_DIR}
    tools/console ${IP_ADDR}:${PORT} -c 'setup_datastore()' && export INIT_DATASTORE=1 || echo "Setting datastore failed!"
fi
