#!/bin/bash

xhost +
docker exec -it --privileged -e DISPLAY=${DISPLAY} dtc-ros-jazzy-atak bash
xhost -