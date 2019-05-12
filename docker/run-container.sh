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


IMAGE_NAME=$1
CONTAINER_NAME=$2

PRJ_DIR=$(dirname $(pwd))

if [ ! -z ${CONTAINER_NAME} ]; then
    docker run -p 8000:8000 -p 8001:8001 -p 49532:8002 --name ${CONTAINER_NAME} -v ${PRJ_DIR}:/opt/personfinder -it ${IMAGE_NAME} bash
else
    docker run -p 8000:8000 -p 8001:8001 -p 49532:8002 -v ${PRJ_DIR}:/opt/personfinder -it ${IMAGE_NAME} bash
fi

