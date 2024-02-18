#! /bin/bash

# Change the IP addresses to match your environment's
export RTSP_URL=rtsp://192.168.1.144:8554/mjpeg/1

export T_LITE_URL=http://192.168.1.145/json

# shift the thermal image this number of pixels to your right (positive value), negative value otherwise
export X_OFFSET=0
# shift the thermal image this number of pixels up (positvie value), negative value otherwise
export Y_OFFSET=0

# set the level of transparency while overlapping the normal image to the thermal image
export ALPHA=0.7
