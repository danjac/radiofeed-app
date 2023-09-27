#!/usr/bin/env bash

set -o errexit

# Mailhog
podman run -dt -p 1025:1025 -p 8025:8025 mailhog/mailhog

# Redis
podman run -dt -p 6379:6379 redis:7.0.5-bullseye

# PostgreSQL

podman run -dt -e POSTGRES_PASSWORD=password \
    -v pg_data:/var/lib/postgresql/data \
    -p 5432:5432 postgres:15.0-bullseye
