# Deployment Guide

Fresh install of Radiofeed on a Hetzner Cloud K3s cluster with Cloudflare CDN/SSL.

## Architecture

| Layer | Tool | What it does |
|-------|------|--------------|
| Infrastructure | Terraform (hetzner) | Servers, network, firewall, Postgres volume; K3s installed via cloud-init |
| DNS / CDN / SSL | Terraform (cloudflare) | DNS A record, CDN caching, TLS settings |
| Kubernetes objects | Helm (`helm/radiofeed/`) | Postgres, Redis, Django app, workers, cron jobs, ingress |
| Observability | Helm (`helm/observability/`) | Prometheus, Grafana, Loki, Tempo, OTel |

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.0
- [Helm](https://helm.sh/docs/intro/install/) >= 3.0
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [hcloud CLI](https://github.com/hetznercloud/cli) — install then:
  ```bash
  hcloud context create radiofeed   # paste a Read & Write API token when prompted
  ```
  Get the token: Hetzner Console → your project → Security → API Tokens → Generate.
- [just](https://github.com/casey/just)
- SSH key pair (`ssh-keygen -t ed25519`)
- Cloudflare account with your domain added and nameservers updated

---

## Step 1 — Provision Hetzner infrastructure

```bash
cd terraform/hetzner
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars
```

Required values:

| Variable | Description |
|----------|-------------|
| `hcloud_token` | Hetzner Cloud API token (Read & Write) |
| `ssh_public_key` | Contents of `~/.ssh/id_ed25519.pub` |
| `k3s_token` | Random string for K3s cluster auth — `openssl rand -hex 32` |
| `cluster_name` | Name prefix for all resources (e.g. `radiofeed`) |

```bash
terraform init
terraform plan    # review
terraform apply   # ~3–5 min; K3s installs via cloud-init in the background
```

Note the server IP for the next step:

```bash
terraform output server_public_ip
```

See [`terraform/hetzner/README.md`](terraform/hetzner/README.md) for all variables and scaling options.

---

## Step 2 — Configure Cloudflare

```bash
cd ../cloudflare
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars
```

Set `cloudflare_api_token`, `domain`, and `server_ip` (from Step 1).

```bash
terraform init
terraform apply
```

### Create origin certificates

1. Cloudflare Dashboard → SSL/TLS → Origin Server → Create Certificate (15-year validity)
2. Keep the browser tab open — you'll paste these into `values.secret.yaml` in Step 4.

See [`terraform/cloudflare/README.md`](terraform/cloudflare/README.md) for Mailgun DNS setup and troubleshooting.

---

## Step 3 — Wait for K3s and fetch kubeconfig

K3s finishes installing a few minutes after `terraform apply` completes. Check:

```bash
ssh ubuntu@$(cd terraform/hetzner && terraform output -raw server_public_ip) \
    'k3s kubectl get nodes'
```

All nodes should show `Ready`. Then fetch the kubeconfig:

```bash
just get-kubeconfig
kubectl --kubeconfig ~/.kube/radiofeed.yaml get nodes  # sanity check
```

---

## Step 4 — Configure Helm values

### radiofeed chart

```bash
cp helm/radiofeed/values.secret.yaml.example helm/radiofeed/values.secret.yaml
$EDITOR helm/radiofeed/values.secret.yaml
```

Fill in all secrets, including `postgres.volumePath`:

```bash
terraform -chdir=terraform/hetzner output -raw postgres_volume_mount_path
# e.g. /mnt/HC_Volume_12345678
```

```yaml
# helm/radiofeed/values.secret.yaml
postgres:
  volumePath: "/mnt/HC_Volume_12345678"
```

Also set `domain` in `values.yaml`:

```yaml
domain: example.com
```

### Resource limits

Both charts ship defaults tuned for the Terraform default server type (`cx23`: 2 vCPU, 4 GB RAM).
If you change `server_type`, `database_server_type`, or `agent_server_type` in `terraform.tfvars`,
override the corresponding resource values in `values.secret.yaml`.

**radiofeed chart** — one block per workload, all under `resources:`:

| Key | Node | Default request | Default limit |
|-----|------|-----------------|---------------|
| `resources.app` | webapp | 256Mi / 200m | 768Mi / 1000m |
| `resources.worker` | jobrunner | 256Mi / 200m | 768Mi / 1000m |
| `resources.cronjob` | jobrunner | 128Mi / 100m | 512Mi / 500m |
| `resources.postgres` | database | 512Mi / 200m | 1536Mi / 1000m |
| `resources.redis` | database | 64Mi / 50m | 256Mi / 200m |

Example override in `helm/radiofeed/values.secret.yaml`:

```yaml
resources:
  app:
    requests:
      memory: 512Mi
      cpu: 500m
    limits:
      memory: 1536Mi
      cpu: 1500m
```

**observability chart** — all components run on the server node alongside k3s + etcd + Traefik.
Limits are set per component (Prometheus, Grafana, Loki, Tempo, OTel agent/gateway) and can be
overridden in `helm/observability/values.secret.yaml` using the same key paths as `values.yaml`.

### observability chart (optional)

```bash
cp helm/observability/values.secret.yaml.example helm/observability/values.secret.yaml
$EDITOR helm/observability/values.secret.yaml   # set Grafana admin password + hostname
```

---

## Step 5 — Deploy

> **Prerequisite**: `just get-kubeconfig` (Step 3) must have run successfully before this.
> All `helm-upgrade`, `helm-upgrade-observability`, `kube`, `rdj`, and `rpsql` commands
> read `~/.kube/radiofeed.yaml`. Override the path with `KUBECONFIG=/other/path just helm-upgrade`.

```bash
just helm-upgrade
```

Wait for all pods to come up:

```bash
just kube get pods -n default
```

---

## Step 6 — Post-deployment

```bash
just rdj migrate           # run database migrations
just rdj createsuperuser   # create admin user
```

Visit `https://your-domain/admin/` to verify. Update the Site domain in Django admin → Sites.

---

## Step 7 — Deploy observability (optional)

```bash
just helm-upgrade-observability
just kube get pods -n monitoring
```

Grafana is available at the hostname set in `helm/observability/values.secret.yaml`.

---

## Day-2 operations

### Deploy a new image

```bash
just deploy ghcr.io/danjac/radiofeed-app:sha-abc123
```

This runs the release job (migrations, collectstatic) then rolls out the new image.

### CI/CD deployment (GitHub Actions)

The `deploy` workflow (`.github/workflows/deploy.yml`) runs `scripts/deploy.sh` directly
on the GitHub Actions runner using `kubectl` and `helm`. Two repository secrets are required:

| Secret | Description |
|--------|-------------|
| `KUBECONFIG_BASE64` | Base64-encoded kubeconfig (see below) |
| `HELM_VALUES_SECRET` | Full contents of `helm/radiofeed/values.secret.yaml` |

Generate `KUBECONFIG_BASE64`:

```bash
base64 -w0 ~/.kube/radiofeed.yaml
# macOS: base64 -i ~/.kube/radiofeed.yaml
```

Set these in GitHub → repository **Settings → Secrets and variables → Actions**.

The workflow is triggered manually via **Actions → radiofeed:deploy → Run workflow**.

### Run management commands

```bash
just rdj migrate
just rdj createsuperuser
just rdj shell
```

### Connect to the production database

```bash
just rpsql
```

### kubectl access

```bash
just kube get pods
just kube logs -f deployment/django-app
```

### Scale webapp nodes

Edit `terraform/hetzner/terraform.tfvars`:

```hcl
webapp_count = 3
```

Then `terraform apply` and `just helm-upgrade` (updates replica count to match).

### Tune resource limits after resizing nodes

After changing `server_type`, `database_server_type`, or `agent_server_type` in Terraform and
running `terraform apply`, update the matching resource blocks in `helm/radiofeed/values.secret.yaml`
and (for the server node) `helm/observability/values.secret.yaml`, then redeploy:

```bash
just helm-upgrade
just helm-upgrade-observability
```

To check current resource usage on the cluster:

```bash
just kube top pods
just kube top nodes
```

### Upgrade PostgreSQL major version

See `scripts/pg-upgrade.sh` and the `pgUpgrade` section in `helm/radiofeed/values.yaml`.
