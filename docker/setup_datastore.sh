#!/usr/bin/env bash
# Copyright 2019 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# Initialize the Person Finder's datastore the first time it is run on this machine.

PORT=8000
IP_ADDR=`ip addr list eth0 | grep 'inet ' | cut -d' ' -f6 | cut -d'/' -f1`

if [ 0 = ${INIT_DATASTORE} ]; then
    echo "Setting datastore for server at ${IP_ADDR}:${PORT}"
    cd ${PERSONFINDER_DIR}
    tools/console ${IP_ADDR}:${PORT} -c 'setup_datastore()' && export INIT_DATASTORE=1 || echo "Setting datastore failed!"
fi
