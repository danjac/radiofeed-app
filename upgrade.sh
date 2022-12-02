#!/usr/bin/env bash


# Python dependencies

poetry update

# Frontend dependencies

npm run check-updates
npm install

# Pre-commit dependencies

pre-commit autoupdate
