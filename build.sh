#!/bin/bash

set -o errexit
set -o nounset

buildah bud -t audiotrails .

#buildah push docker.io/library/audiotrails-django:latest docker://danjac2018/audiotrails-django:latest


