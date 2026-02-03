# Hetzner Cloud Infrastructure with Terraform

This directory contains Terraform configuration for provisioning RadioFeed infrastructure on Hetzner Cloud. The infrastructure consists of multiple servers for running a K3s cluster with separate nodes for control plane, database, job processing, and web applications.

## Architecture

The Terraform configuration creates the following infrastructure:

- **1 Server Node** (k3s control plane + Traefik load balancer)
  - Ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)
  - Public IP for external access
  - Private IP: 10.0.0.1 (configurable)

- **1 Database Node** (PostgreSQL + Redis)
  - Dedicated volume for PostgreSQL data
  - Port 22 (SSH) for management
  - All traffic within private network

- **1 Job Runner Node** (for cron jobs)
  - Runs scheduled tasks (feed parsing, notifications, recommendations)
  - Port 22 (SSH) for management
  - All traffic within private network

- **N Web Application Nodes** (default: 2)
  - Runs Django web application containers
  - Port 22 (SSH) for management
  - All traffic within private network

- **Private Network** (10.0.0.0/16)
  - Secure internal communication between nodes
  - All nodes connected via private network

- **Firewall Rules**
  - Server: SSH (22), HTTP (80), HTTPS (443) from internet
  - Agents: SSH (22) from internet, all traffic from private network

- **PostgreSQL Volume** (default: 50 GB)
  - Persistent storage for database data
  - Automatically attached to database node

## Prerequisites

1. **Hetzner Cloud Account**
   - Sign up at https://www.hetzner.com/cloud
   - Create a new project

2. **Hetzner Cloud API Token**
   - Go to: Cloud Console → Project → Security → API Tokens
   - Create a new token with Read & Write permissions
   - Copy the token (you'll need it for terraform.tfvars)

3. **Terraform**
   - Install Terraform >= 1.0: https://www.terraform.io/downloads
   - Or use: `brew install terraform` (macOS) / `apt install terraform` (Ubuntu)

4. **SSH Key Pair**
   - Generate if you don't have one: `ssh-keygen -t rsa -b 4096 -C "your-email@example.com"`
   - Your public key will be used for server access

5. **Cloudflare Account** (for production)
   - Set up DNS and obtain origin certificates (for Ansible deployment)

## Setup

### 1. Configure Terraform Variables

Copy the example variables file and edit it with your settings:

```bash
cd terraform/hetzner
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set:
- `hcloud_token` - Your Hetzner Cloud API token
- `ssh_public_key` - Your SSH public key (from ~/.ssh/id_rsa.pub)
- `cluster_name` - Name prefix for resources (default: "radiofeed")
- `location` - Hetzner datacenter (default: "nbg1")
- `webapp_count` - Number of webapp instances (default: 2)
- Other optional settings (server types, network ranges, etc.)

**Important**: Never commit `terraform.tfvars` to version control (already in .gitignore).

### 2. Initialize Terraform

```bash
terraform init
```

This downloads the Hetzner Cloud provider plugin.

### 3. Preview Changes

```bash
terraform plan
```

Review the resources that will be created. Expected output:
- 1 network + 1 subnet
- 2 firewalls
- 1 SSH key
- 5 servers (1 server + 1 database + 1 jobrunner + 2 webapps)
- 1 volume
- Network attachments for all servers

### 4. Create Infrastructure

```bash
terraform apply
```

Type `yes` to confirm. This will:
1. Create the private network
2. Create firewalls
3. Register SSH key
4. Create volume for PostgreSQL
5. Provision all servers
6. Attach servers to private network
7. Mount volume to database node

This takes ~2-3 minutes.

### 5. Get Server IPs

After `terraform apply` completes, you'll see output with all server IPs:

```bash
terraform output
```

Or get the Ansible inventory snippet:

```bash
terraform output -raw ansible_inventory > ../../ansible/hosts.yml
```

This creates a ready-to-use `hosts.yml` file for Ansible.

## Using with Ansible

After Terraform provisions the infrastructure, use Ansible to deploy the application:

### 1. Update Ansible Inventory

Option A: Use Terraform output (recommended)
```bash
cd terraform/hetzner
terraform output -raw ansible_inventory > ../../ansible/hosts.yml
```

Option B: Manually copy IPs from `terraform output` to `ansible/hosts.yml`

### 2. Update Ansible Variables

Edit `ansible/hosts.yml` and set:
- `domain` - Your domain name
- `admin_url` - Custom admin path
- `admins` - Admin email addresses
- `secret_key` - Generate with `python manage.py generate_secret_key`
- `postgres_password` - Secure database password
- `mailgun_api_key` - Mailgun API key (if using email)
- `sentry_url` - Sentry DSN (if using error tracking)

### 3. Encrypt Sensitive Data

```bash
cd ../../ansible
ansible-vault encrypt hosts.yml
```

Set a vault password and store it securely.

### 4. Prepare SSH Keys and Certificates

```bash
cd ansible

# Add SSH public keys for all users
cp ~/.ssh/id_rsa.pub ssh-keys/admin.pub

# Copy Cloudflare origin certificates
cp /path/to/cloudflare.pem certs/
cp /path/to/cloudflare.key certs/
```

### 5. Configure Cloudflare CDN + SSL (Recommended)

**Option A: Using Terraform (Recommended)**

Use the Cloudflare Terraform configuration to automatically set up DNS, CDN, and SSL:

```bash
cd ../cloudflare
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with:
#   - Cloudflare API token
#   - Your domain name
#   - Server IP from Hetzner (terraform output server_public_ip)
terraform init
terraform apply
```

This will configure:
- DNS A record pointing to your server
- CDN caching for static assets and media
- SSL/TLS with full mode
- Security headers and firewall rules

**Option B: Manual DNS Setup**

If not using Cloudflare or Terraform:
- Create an `A` record pointing to the **server node public IP**
- Get server IP: `terraform output server_public_ip`

**Important: Origin Certificates**

The Ansible deployment requires Cloudflare origin certificates:

1. Go to Cloudflare Dashboard → SSL/TLS → Origin Server
2. Click "Create Certificate"
3. Save certificate as `../../ansible/certs/cloudflare.pem`
4. Save private key as `../../ansible/certs/cloudflare.key`

See [`../cloudflare/README.md`](../cloudflare/README.md) for detailed Cloudflare setup instructions.

### 6. Deploy with Ansible

From project root:

```bash
just apb site
```

This will:
- Set up all servers
- Install K3s cluster
- Deploy PostgreSQL and Redis
- Deploy the Django application
- Configure Traefik load balancer
- Set up SSL/TLS with Cloudflare certificates
- Configure cron jobs

See `ansible/README.md` for more deployment details.

## Scaling

### Add More Webapp Nodes

Edit `terraform.tfvars`:
```hcl
webapp_count = 3  # or more
```

Then:
```bash
terraform apply
```

Update `ansible/hosts.yml` with the new server IPs and re-run Ansible.

### Upgrade Server Types

Edit `terraform.tfvars`:
```hcl
database_server_type = "cx42"  # 8 vCPU, 16 GB RAM
```

Then:
```bash
terraform apply
```

**Warning**: Changing server types causes server recreation (downtime).

### Increase PostgreSQL Volume

Edit `terraform.tfvars`:
```hcl
postgres_volume_size = 100  # GB
```

Then:
```bash
terraform apply
```

Volumes can be resized without data loss.

## Backup and Disaster Recovery

### Backup Important Files

Before making changes, back up:

```bash
# Terraform state
cp terraform.tfstate terraform.tfstate.backup

# Ansible inventory
cp ../../ansible/hosts.yml ../../ansible/hosts.yml.backup
```

### Server Snapshots

Create snapshots in Hetzner Cloud Console:
- Cloud Console → Servers → Select server → Snapshots → Create snapshot

### PostgreSQL Backups

The Ansible deployment includes automated PostgreSQL backups. See `ansible/README.md` for details.

## Destroying Infrastructure

**Warning**: This will permanently delete all servers and data.

```bash
terraform destroy
```

Type `yes` to confirm.

**Important**: Take PostgreSQL backups before destroying!

## Troubleshooting

### Error: "Authentication failed"
- Check that `hcloud_token` in `terraform.tfvars` is correct
- Verify token has Read & Write permissions

### Error: "SSH key already exists"
- Remove the existing key in Hetzner Console, or
- Change `cluster_name` in `terraform.tfvars`

### Error: "Resource limit exceeded"
- Check your Hetzner Cloud project limits
- Contact Hetzner support to increase limits

### Servers not accessible via SSH
- Check that `ssh_public_key` in `terraform.tfvars` matches your private key
- Verify firewall rules: `terraform state show hcloud_firewall.server`
- Check Hetzner Cloud Console → Servers → Select server → Networking

### Private network not working
- Ensure all servers are in the same network zone
- Check network attachments: `terraform output network_id`
- Verify subnet IP range doesn't overlap with other networks

## Advanced Configuration

### Custom Network Ranges

Edit `terraform.tfvars`:
```hcl
network_ip_range  = "172.16.0.0/16"
subnet_ip_range   = "172.16.0.0/24"
server_private_ip = "172.16.0.1"
```

### Different Datacenter Locations

Available locations and their network zones:

| Location | Zone | Region |
|----------|------|--------|
| nbg1 | eu-central | Nuremberg, Germany |
| fsn1 | eu-central | Falkenstein, Germany |
| hel1 | eu-central | Helsinki, Finland |
| ash | us-east | Ashburn, USA |
| hil | us-west | Hillsboro, USA |

Edit `terraform.tfvars`:
```hcl
location     = "fsn1"
network_zone = "eu-central"
```

### Use Different OS Image

Edit `terraform.tfvars`:
```hcl
server_image = "ubuntu-22.04"  # or "debian-12", etc.
```

**Note**: Ansible playbooks are tested with Ubuntu 24.04.

## Resources

- [Hetzner Cloud Documentation](https://docs.hetzner.com/cloud/)
- [Terraform Hetzner Provider](https://registry.terraform.io/providers/hetznercloud/hcloud/latest/docs)
- [K3s Documentation](https://docs.k3s.io/)
- [Ansible Documentation](https://docs.ansible.com/)

## Support

For issues related to:
- Infrastructure provisioning → Check this README
- Application deployment → See `ansible/README.md`
- Application bugs → See project root `README.md`
