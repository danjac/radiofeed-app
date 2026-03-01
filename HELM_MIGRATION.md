# Helm Migration Guide

Migrates the existing Ansible-managed cluster to the new Terraform + Helm stack.
The PostgreSQL Hetzner volume is preserved; all servers are replaced.

## Prerequisites

- `hcloud` CLI configured — if you haven't used it before:
  1. Hetzner Console → your project → Security → API Tokens → Generate API Token (Read & Write)
  2. `hcloud context create radiofeed` (paste the token when prompted)
  The context is automatically active after creation.
- `terraform` ≥ 1.0
- `helm` ≥ 3.0
- `kubectl`
- `just`

---

## Step 1 — Record the existing volume ID

```bash
hcloud volume list
```

Note the **ID** of the postgres volume (e.g. `12345678`) and its **name**.
The mount path on the database server will be `/mnt/HC_Volume_<ID>`.

Confirm the volume is healthy before proceeding:

```bash
ssh ubuntu@<DATABASE_IP> 'df -h | grep HC_Volume && ls /mnt/HC_Volume_*'
```

---

## Step 2 — Take the old cluster offline

Scale down application workloads so no new writes reach Postgres:

```bash
# Using the old kubectl.sh script, or via kubeconfig directly
kubectl scale deployment django-app django-worker --replicas=0 -n default
kubectl get pods -n default  # wait until app pods are gone
```

Stop Postgres:

```bash
kubectl scale statefulset postgres --replicas=0 -n default
kubectl get pods -n default  # wait until postgres pod is gone
```

---

## Step 3 — Detach the Postgres volume

```bash
hcloud volume detach <VOLUME_NAME_OR_ID>
```

Verify:

```bash
hcloud volume describe <VOLUME_NAME_OR_ID>
# "Server" should show "Not attached"
```

---

## Step 4 — Delete the old servers

```bash
hcloud server list
hcloud server delete <server-name> <database-name> <jobrunner-name> <webapp-name>...
```

The volume is now floating (unattached) and safe.

---

## Step 5 — Prepare Terraform

### 5a. Fill in terraform.tfvars

```bash
cd terraform/hetzner
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars
```

Set `k3s_token` to a random string (min 16 chars):

```bash
openssl rand -hex 32
```

### 5b. Import the existing Postgres volume

This tells Terraform to adopt the existing volume instead of the new empty one it created.

If `terraform apply` already ran and created a fresh volume, remove it from state first
(this does **not** delete the cloud resource — it just untracks it):

```bash
cd terraform/hetzner
terraform state rm hcloud_volume.postgres
```

Then import the real volume:

```bash
terraform import hcloud_volume.postgres <VOLUME_ID>
```

You can now safely delete the empty volume Terraform created via the Hetzner Console
or `hcloud volume delete <name>` — it has no data.

Verify Terraform sees the correct volume:

```bash
terraform state show hcloud_volume.postgres
# Should show the existing volume name and size
```

### 5c. Apply

```bash
terraform plan   # review — should show new servers + volume attachment, no volume replace
terraform apply
```

`terraform apply` will:
- Create new servers (server, database, jobrunner, webapp)
- Run K3s cloud-init on each server
- Attach the existing Postgres volume to the new database server
- Run the background `postgres-volume-perms.sh` script on the database node
  (sets `chown 999:999` on the volume mount — fast since ownership is unchanged)

---

## Step 6 — Wait for the cluster

K3s cloud-init runs asynchronously. Wait until all nodes are Ready (typically 3–5 minutes):

```bash
# SSH into the server node and watch
ssh ubuntu@$(terraform output -raw server_public_ip) \
    'watch k3s kubectl get nodes'
```

All nodes should show `Ready`.

---

## Step 7 — Fetch kubeconfig

```bash
just get-kubeconfig
kubectl --kubeconfig ~/.kube/radiofeed.yaml get nodes  # sanity check
```

---

## Step 8 — Prepare Helm values

### 8a. Set the Postgres volume path

Get the mount path from Terraform output:

```bash
terraform -chdir=terraform/hetzner output -raw postgres_volume_mount_path
# e.g. /mnt/HC_Volume_12345678
```

Edit `helm/radiofeed/values.yaml`:

```yaml
postgres:
  volumePath: /mnt/HC_Volume_12345678   # <-- replace CHANGEME
```

### 8b. Create values.secret.yaml

```bash
cp helm/radiofeed/values.secret.yaml.example helm/radiofeed/values.secret.yaml
$EDITOR helm/radiofeed/values.secret.yaml
```

Fill in all required secrets. The `postgresPassword` must match the password
already stored in the existing Postgres data directory — use the value from the
old cluster's secrets (Ansible vault or wherever it was stored).

---

## Step 9 — Deploy the radiofeed chart

```bash
just helm-upgrade
```

Helm will create the namespace objects. Postgres starts first (the StatefulSet
mounts the existing volume), then the app deploys once Postgres is ready.

Wait for all pods to come up:

```bash
just kube get pods -n default
```

---

## Step 10 — Verify

```bash
# Check Postgres has the existing data
just rpsql -c '\l'           # should show your databases

# Run any pending migrations
just rdj migrate

# Check the app is serving traffic
curl -I https://<your-domain>
```

---

## Step 11 — Deploy observability (optional)

```bash
cp helm/observability/values.secret.yaml.example helm/observability/values.secret.yaml
$EDITOR helm/observability/values.secret.yaml  # set Grafana admin password and hostname

just helm-upgrade-observability
```

---

## Rollback

If something goes wrong before Step 9 (no Helm deploy yet), the Postgres volume is
intact and unmodified. Re-attach it to any server manually:

```bash
hcloud server create ...   # or restore old server from snapshot if available
hcloud volume attach <VOLUME_ID> --server <SERVER_ID> --automount
```

If something goes wrong after Step 9, the data is still in the volume. Scale Postgres
to 0, inspect the data directory, and re-deploy.
