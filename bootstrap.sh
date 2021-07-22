#!/bin/bash

set -o errexit
set -o nounset

export UID="$UID"
export GID="$GID"
docker-compose up
