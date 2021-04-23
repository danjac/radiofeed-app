#!/bin/bash

set -o errexit
set -o nounset

podman build -t audiotrails:latest .

# build and deploy image to Docker Hub
#podman build -t docker.io/danjac2018/audiotrails:latest .
#podman login docker.io
#podman push docker.io/danjac2018/audiotrails:latest
