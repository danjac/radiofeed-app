#!/usr/bin/env bash
# Open a psql session inside the production postgres pod.
# Usage: psql.sh [psql_args...]
set -euo pipefail

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/radiofeed.yaml}"

POD="$(kubectl get pods -l app=postgres -n default -o jsonpath='{.items[0].metadata.name}')"
kubectl exec -it "$POD" -n default -- psql -U postgres "$@"
