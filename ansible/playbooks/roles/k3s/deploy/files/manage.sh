#!/usr/bin/env bash

set -o errexit

export KUBECONFIG="$HOME/.kube/config"

kubectl exec -it "$(kubectl get pods -l app=django-app -n default -o jsonpath='{.items[0].metadata.name}')" -n default -- python manage.py "$@"
