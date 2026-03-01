#!/usr/bin/env bash
# Fetch kubeconfig from the K3s server and write it to ~/.kube/radiofeed.yaml
# (or the path in $KUBECONFIG if overridden).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SERVER_IP="$(cd "$REPO_ROOT/terraform/hetzner" && terraform output -raw server_public_ip)"
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/radiofeed.yaml}"

mkdir -p "$(dirname "$KUBECONFIG_PATH")"

ssh "ubuntu@$SERVER_IP" 'cat /home/ubuntu/.kube/config' \
    | sed "s/127.0.0.1/$SERVER_IP/g" \
    > "$KUBECONFIG_PATH"

echo "Kubeconfig written to $KUBECONFIG_PATH"
