# terraform/hetzner

Provisions the Hetzner Cloud infrastructure for the Radiofeed K3s cluster.
K3s is installed automatically via cloud-init on first boot — no Ansible required.

## What gets created

| Resource | Count | Notes |
|----------|-------|-------|
| Private network + subnet | 1 | `10.0.0.0/16`, zone configurable |
| Firewalls | 2 | server (80/443/22 public) + agents (22 public, all private) |
| SSH key | 1 | Registered in Hetzner for server access |
| Server node | 1 | K3s control plane + Traefik; private IP `10.0.0.2` |
| Database node | 1 | K3s agent, role=database; private IP `10.0.0.3` |
| Job runner node | 1 | K3s agent, role=jobrunner; private IP `10.0.0.4` |
| Webapp nodes | N | K3s agents, role=webapp; private IPs `10.0.0.5+` |
| PostgreSQL volume | 1 | Hetzner block storage, ext4, attached to database node |

Private IPs are fixed via `cidrhost()` so K3s agents can join the cluster during cloud-init.

## Cloud-init provisioning

Each server type has a dedicated cloud-init template:

| Template | Used by | What it does |
|----------|---------|--------------|
| `cloud_init_server.tftpl` | server node | Installs K3s server, sets up kubeconfig, pins CoreDNS/Traefik/metrics-server to server node |
| `cloud_init_agent.tftpl` | jobrunner, webapps | Polls for K3s server readiness, installs K3s agent with correct role label |
| `cloud_init_database.tftpl` | database node | Same as agent + background script to set Postgres volume permissions |

Cloud-init runs once on first boot. `lifecycle { ignore_changes = [user_data] }` prevents
server recreation when templates are updated.

## Setup

```bash
cd terraform/hetzner
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars
terraform init
terraform plan
terraform apply
```

## Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `hcloud_token` | yes | — | Hetzner Cloud API token (Read & Write) |
| `ssh_public_key` | yes | — | SSH public key for server access |
| `k3s_token` | yes | — | Pre-shared token for K3s cluster (`openssl rand -hex 32`) |
| `cluster_name` | no | `radiofeed` | Name prefix for all resources |
| `location` | no | `nbg1` | Hetzner datacenter |
| `network_zone` | no | `eu-central` | Must match `location` |
| `server_type` | no | `cx22` | Server node type |
| `database_server_type` | no | `cx22` | Database node type |
| `agent_server_type` | no | `cx22` | Jobrunner and webapp node type |
| `webapp_count` | no | `2` | Number of webapp nodes |
| `postgres_volume_size` | no | `50` | Postgres volume size in GB |

Available locations:

| Location | Zone | Region |
|----------|------|--------|
| `nbg1` | `eu-central` | Nuremberg, Germany |
| `fsn1` | `eu-central` | Falkenstein, Germany |
| `hel1` | `eu-central` | Helsinki, Finland |
| `ash` | `us-east` | Ashburn, USA |
| `hil` | `us-west` | Hillsboro, USA |

## Outputs

```bash
terraform output server_public_ip          # for Cloudflare terraform.tfvars
terraform output -raw postgres_volume_mount_path  # for helm/radiofeed/values.yaml
terraform output get_kubeconfig_cmd        # the command just get-kubeconfig runs
```

## Scaling

### Add webapp nodes

```hcl
# terraform.tfvars
webapp_count = 3
```

```bash
terraform apply
just helm-upgrade   # updates replica count
```

### Upgrade server types

```hcl
database_server_type = "cx32"
```

```bash
terraform apply   # causes server recreation (brief downtime for that node)
```

### Increase Postgres volume

```hcl
postgres_volume_size = 100
```

```bash
terraform apply   # live resize, no data loss
```

## Troubleshooting

**K3s not ready after apply** — cloud-init runs asynchronously. Check progress:

```bash
ssh ubuntu@$(terraform output -raw server_public_ip) 'tail -f /var/log/cloud-init-output.log'
```

**Nodes not joining** — verify `k3s_token` is identical across `terraform.tfvars`
and not been changed since initial provision.

**Postgres volume permissions** — the background script logs to
`/var/log/postgres-volume-perms.log` on the database node.

**SSH key already exists** — either remove it in Hetzner Console, or change `cluster_name`.
