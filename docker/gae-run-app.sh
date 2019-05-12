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


PORT=8000
HOST_PORT=8001
API_PORT=49532

IP_ADDR=`ip addr list eth0 | grep 'inet ' | cut -d' ' -f6 | cut -d'/' -f1`

cd ${PERSONFINDER_DIR}
echo "Starting Person Finder server"
tools/gae run app --host ${IP_ADDR} --port ${PORT} --admin_host=${IP_ADDR} --admin_port=${HOST_PORT} --api_host=${IP_ADDR} --api_port=${API_PORT} --skip_sdk_update_check
echo "Person Finder server stopped"
