#!/usr/bin/env bash

set -o errexit


docker compose exec postgres psql -U postgres
