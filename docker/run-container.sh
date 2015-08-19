#!/usr/bin/env bash

IMAGE_NAME=$1
CONTAINER_NAME=$2

docker run --name ${CONTAINER_NAME} -v ~/workspace/personfinder:/opt/personfinder -p 127.0.0.1:8000:8000 -it ${IMAGE_NAME} /bin/bash
