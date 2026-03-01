#!/usr/bin/env bash
# Deploy a new image to production.
# Runs the release job (migrations, collectstatic) then upgrades the Helm chart.
# Usage: IMAGE=ghcr.io/example/radiofeed:sha-abc123 deploy.sh
set -euo pipefail

if [ -z "${IMAGE:-}" ]; then
    echo "ERROR: IMAGE environment variable is not set."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/radiofeed.yaml}"

echo "Deploying image $IMAGE ..."

# ── Release job (runs ./release.sh: migrate, collectstatic, etc.) ────────────
RELEASE_JOB_ID="$(head -c 12 /dev/urandom | base64 | tr -dc 'a-z0-9' | head -c 12)"
RELEASE_JOB_NAME="django-release-job-$RELEASE_JOB_ID"

kubectl apply -f - -n default <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: $RELEASE_JOB_NAME
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      nodeSelector:
        role: jobrunner
      containers:
        - name: django
          image: $IMAGE
          command: ["/bin/sh", "-c"]
          args: ["./release.sh"]
          envFrom:
            - configMapRef:
                name: configmap
            - secretRef:
                name: secrets
EOF

kubectl wait --for=condition=Ready pod \
    -l "job-name=$RELEASE_JOB_NAME" -n default --timeout=60s
kubectl logs --follow "job/$RELEASE_JOB_NAME" -n default
kubectl wait --for=condition=complete "job/$RELEASE_JOB_NAME" -n default --timeout=60s
kubectl delete "job/$RELEASE_JOB_NAME" -n default

# ── Helm upgrade ─────────────────────────────────────────────────────────────
helm upgrade radiofeed "$REPO_ROOT/helm/radiofeed/" \
    --kubeconfig "$KUBECONFIG" \
    --set "image=$IMAGE" \
    -f "$REPO_ROOT/helm/radiofeed/values.yaml" \
    -f "$REPO_ROOT/helm/radiofeed/values.secret.yaml"

echo "Deploy complete."
