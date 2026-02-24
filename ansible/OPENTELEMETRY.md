# OpenTelemetry Observability Stack

Self-hosted LGTM stack (Loki + Grafana + Tempo + Mimir/Prometheus) deployed to the `server` node via the `k3s_observability` Ansible role.

## Architecture

| Component | Kind | Node | Purpose |
|-----------|------|------|---------|
| OTel Agent | DaemonSet (all nodes) | all | Collects host metrics and container logs |
| OTel Gateway | Deployment | server | Receives OTLP traces from Django; routes all signals to backends |
| Prometheus | Deployment | server | Metrics storage (receives via remote write from gateway) |
| Loki | Deployment | server | Log storage |
| Tempo | Deployment | server | Trace storage |
| Grafana | Deployment | server | UI — datasources pre-configured with cross-linking |

Django is already instrumented with OpenTelemetry (traces for Django, Psycopg, Redis, and Requests). Setting `OPEN_TELEMETRY_URL` activates it.

## Pre-deployment checklist

### 1. Set required variables in `hosts.yml`

```yaml
# Point Django's OTel exporter at the gateway
k3s_deploy_open_telemetry_url: "http://otel-gateway.default.svc.cluster.local:4318"

# Grafana admin password (required)
k3s_observability_grafana_password: "your-strong-password"
```

### 2. Verify the Cloudflare origin certificate

The cert at `ansible/certs/cloudflare.pem` must cover `*.yourdomain.com` (wildcard) or
explicitly include `grafana.yourdomain.com`. Decrypt and inspect it to check:

```bash
ansible-vault decrypt --output=/tmp/cf.pem ansible/certs/cloudflare.pem
openssl x509 -in /tmp/cf.pem -noout -ext subjectAltName
rm /tmp/cf.pem
```

If the cert does not cover the Grafana subdomain, create a new wildcard Cloudflare origin
certificate in the Cloudflare dashboard (SSL/TLS → Origin Server → Create Certificate, using
`*.yourdomain.com`), update the vault-encrypted files, and re-run the deploy.

The Grafana IngressRoute reuses the existing `cloudflare-origin-cert` Kubernetes secret. The
record must stay proxied (orange cloud in Cloudflare) so that Cloudflare handles browser TLS —
Cloudflare origin certs are only trusted by Cloudflare's own proxies, not browsers directly.

### 3. Add the Grafana DNS record via Terraform

The Cloudflare Terraform config has been updated with a `grafana_subdomain` variable and a
corresponding A record. Apply it:

```bash
cd terraform/cloudflare
terraform plan
terraform apply
```

This creates `grafana.yourdomain.com → server_ip` as a proxied A record. The default subdomain
is `grafana`; override it with `grafana_subdomain` in `terraform.tfvars` if needed.

## Deploy

```bash
just apb deploy
```

Or as part of a full initial deploy:

```bash
just apb site
```

## Browser access

Once deployed, Grafana is available at:

```
https://grafana.yourdomain.com
```

Log in with username `admin` and the password set in `k3s_observability_grafana_password`.
Anonymous access and self-registration are disabled.

Prometheus, Loki, and Tempo are internal-only (no Traefik routes). They are accessible from
within the cluster at:

- `http://prometheus.default.svc.cluster.local:9090`
- `http://loki.default.svc.cluster.local:3100`
- `http://tempo.default.svc.cluster.local:3200`

## Configuration defaults

All defaults are in `roles/k3s_observability/defaults/main.yml`. Notable overrides:

| Variable | Default | Description |
|----------|---------|-------------|
| `k3s_observability_grafana_subdomain` | `grafana` | Subdomain for the Grafana UI |
| `k3s_observability_prometheus_retention` | `30d` | Prometheus TSDB retention period |
| `k3s_observability_tempo_retention` | `48h` | Tempo trace retention period |
| `k3s_observability_prometheus_storage` | `20Gi` | Prometheus hostPath volume size |
| `k3s_observability_loki_storage` | `10Gi` | Loki hostPath volume size |
| `k3s_observability_tempo_storage` | `10Gi` | Tempo hostPath volume size |
| `k3s_observability_grafana_storage` | `2Gi` | Grafana hostPath volume size |

Data is persisted to `k3s_observability_data_dir` (default `/var/lib/radiofeed/observability`) on
the server node using hostPath volumes. Each subdirectory is owned by the UID of the
corresponding container process (Prometheus: 65534, Loki/Tempo: 10001, Grafana: 472).
