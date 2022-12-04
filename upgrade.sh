#!/usr/bin/env bash


# Python dependencies

poetry update && poetry export --without-hashes -o requirements.txt

# Frontend dependencies

npm run check-updates
npm install
