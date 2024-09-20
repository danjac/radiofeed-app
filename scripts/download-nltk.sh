#!/usr/bin/env bash

set -o errexit

# download NLTK source files

xargs -I{} python -c "import nltk; nltk.download('{}')" < "${1}"
