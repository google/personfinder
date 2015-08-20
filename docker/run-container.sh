#!/usr/bin/env bash

IMAGE_NAME=$1
CONTAINER_NAME=$2

PRJ_DIR=$(dirname $(pwd))

if [ ! -z ${CONTAINER_NAME} ]; then
    docker run --name ${CONTAINER_NAME} -v ${PRJ_DIR}:/opt/personfinder -p 127.0.0.1:8000:8000 -it ${IMAGE_NAME} /bin/bash
else
    docker run -v ${PRJ_DIR}:/opt/personfinder -p 127.0.0.1:8000:8000 -it ${IMAGE_NAME} /bin/bash
fi

