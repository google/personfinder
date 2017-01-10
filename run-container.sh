#!/usr/bin/env bash

IMAGE_NAME=$1
CONTAINER_NAME=$2

PRJ_DIR=$(dirname $(pwd))

if [ ! -z ${CONTAINER_NAME} ]; then
    docker run -p 8000:8000 -p 8001:8001 -p 49532:8002  -v ${PRJ_DIR}/personfinder/app:/opt/personfinder/app -v ${PRJ_DIR}/personfinder/tools:/opt/personfinder/tools -v ${PRJ_DIR}/personfinder/tests:/opt/personfinder/tests --name ${CONTAINER_NAME} -it ${IMAGE_NAME} bash
else
    docker run -p 8000:8000 -p 8001:8001 -p 49532:8002 -it ${IMAGE_NAME} bash
fi

