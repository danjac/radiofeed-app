#!/usr/bin/env bash
# Run Django manage.py commands inside the production django-app pod.
# Usage: manage.sh <manage_command> [args...]
# Example: manage.sh migrate
set -euo pipefail

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/radiofeed.yaml}"

POD="$(kubectl get pods -l app=django-app -n default -o jsonpath='{.items[0].metadata.name}')"
kubectl exec -it "$POD" -n default -- python manage.py "$@"
