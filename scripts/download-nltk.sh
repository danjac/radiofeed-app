#!/usr/bin/env bash

set -o errexit

# download NLTK source files

SCRIPT_DIR=$(dirname -- "$(readlink -f -- "$0")")

xargs -I{} python -c "import nltk; nltk.download('{}')" < "${SCRIPT_DIR}/nltk.txt"
