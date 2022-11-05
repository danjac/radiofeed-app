#!/usr/bin/env bash


# Python dependencies

poetry update && poetry export --without-hashes -o requirements.txt

# Frontend dependencies

npm update

# Pre-commit dependencies

pre-commit autoupdate
