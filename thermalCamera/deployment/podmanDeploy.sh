#! /bin/bash

# set env variables
. ./setENV.sh
if [ -z "${RTSP_URL}" ]; then
    echo "Populate the setENV.sh script with the correct parameters and try again."
    exit 1
fi

podman run -d --rm \
-e RTSP_URL=${RTSP_URL} \
-e T_LITE_URL=${T_LITE_URL} \
-e X_OFFSET=${X_OFFSET} \
-e Y_OFFSET=${Y_OFFSET} \
-e ALPHA=${ALPHA} \
-p 4000:4000 \
--name thermal-camera \
quay.io/andyyuen/thermalcamera:1.0
