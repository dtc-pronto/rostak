#!/bin/bash

docker build --build-arg user_id=$(id -u) --rm -t ros-jazzy:atak -f Dockerfile.jazzy.atak .
