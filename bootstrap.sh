#!/bin/bash

set -o errexit
set -o nounset

IMAGE=audiotrails:latest
POD=audiopod

echo "building image $IMAGE"
podman build -t $IMAGE .

if podman pod exists $POD
then
    echo "stopping and removing pod $POD"
    podman pod stop $POD
    podman pod rm $POD
fi

podman play kube pod.yml --configmap=configMap.yml
