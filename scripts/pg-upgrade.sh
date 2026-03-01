#!/usr/bin/env bash
# Upgrade PostgreSQL major version by dumping from the old pod and restoring
# into the new one (started via pgUpgrade.enabled=true in values.yaml).
#
# Usage: pg-upgrade.sh <source-statefulset-pod> <target-statefulset-pod>
# Example: pg-upgrade.sh postgres-0 postgres-upgrade-0
set -euo pipefail

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <source-pod> <target-pod>"
    exit 1
fi

SOURCE_POD="$1"
TARGET_POD="$2"
DB_NAME="postgres"
NAMESPACE="default"

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/radiofeed.yaml}"

TS="$(date +%Y%m%d_%H%M%S)"
DUMP_FILE="/tmp/${DB_NAME}_dump_${TS}.sql.gz"

echo "=== Step 1: Dumping database from pod '$SOURCE_POD' ==="
kubectl exec -n "$NAMESPACE" "$SOURCE_POD" -- \
    pg_dump -U postgres -d "$DB_NAME" | gzip > "$DUMP_FILE"
echo "Dump written to $DUMP_FILE ($(du -h "$DUMP_FILE" | awk '{print $1}'))"

echo "=== Step 2: Restoring into pod '$TARGET_POD' ==="
gunzip -c "$DUMP_FILE" | kubectl exec -i -n "$NAMESPACE" "$TARGET_POD" -- \
    psql -U postgres -d "$DB_NAME"

echo "=== Restore complete. Verify, then set pgUpgrade.enabled=false and redeploy. ==="
