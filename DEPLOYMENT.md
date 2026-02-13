# Deployment Guide

This guide covers deploying Radiofeed to a Hetzner Cloud K3s cluster with Cloudflare CDN and SSL. For detailed reference, see [`terraform/hetzner/README.md`](terraform/hetzner/README.md), [`terraform/cloudflare/README.md`](terraform/cloudflare/README.md), and [`ansible/README.md`](ansible/README.md).

## Architecture Overview

- **Hetzner Cloud**: K3s cluster with dedicated server, database, job runner, and webapp nodes on a private network
- **Cloudflare**: DNS, CDN caching, SSL/TLS termination, DDoS protection
- **Ansible**: Deploys K3s, PostgreSQL, Redis, Django app, Traefik ingress, and cron jobs

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.0
- [Ansible](https://docs.ansible.com/)
- [just](https://github.com/casey/just) command runner
- SSH key pair (`ssh-keygen -t rsa -b 4096`)
- Hetzner Cloud account and API token (Read & Write)
- Cloudflare account (free tier) with your domain added and nameservers updated
- Docker image available at `ghcr.io/danjac/radiofeed-app:main` (or build your own)

## Step 1: Provision Hetzner Infrastructure

```bash
cd terraform/hetzner
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your `hcloud_token`, `ssh_public_key`, and desired settings (cluster name, location, server types, webapp count).

```bash
terraform init
terraform plan    # review resources
terraform apply   # creates servers, network, firewall, and PostgreSQL volume (~2-3 min)
```

Note the server public IP:

```bash
terraform output server_public_ip
```

## Step 2: Configure Cloudflare

```bash
cd ../cloudflare
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your `cloudflare_api_token`, `domain`, and the `server_ip` from Step 1.

```bash
terraform init
terraform apply
```

### Create Origin Certificates

1. Go to Cloudflare Dashboard > SSL/TLS > Origin Server
2. Click "Create Certificate" (15-year validity recommended)
3. Save the certificate and key:

```bash
mkdir -p ../../ansible/certs
# Save certificate as ansible/certs/cloudflare.pem
# Save private key as ansible/certs/cloudflare.key
chmod 600 ../../ansible/certs/cloudflare.*
```

### Mailgun DNS Records (Optional)

If using Mailgun for email, add the following DNS records in the Cloudflare Dashboard (DNS > Records):

- **TXT** (SPF): `v=spf1 include:mailgun.org ~all`
- **TXT** (DKIM): copy the `k1._domainkey` (and any additional DKIM) records from Mailgun Dashboard > Sending > Domains > DNS Records
- **MX**: `mxa.mailgun.org` (priority 10) and `mxb.mailgun.org` (priority 10)
- **CNAME** (tracking): `email` pointing to `mailgun.org` (DNS only, not proxied)

Verify the records in Mailgun Dashboard > DNS Records > "Verify DNS Settings". See [`terraform/cloudflare/README.md`](terraform/cloudflare/README.md) for full details.

## Step 3: Generate Ansible Inventory

```bash
cd ../hetzner
terraform output -raw ansible_inventory > ../../ansible/hosts.yml
```

Edit `ansible/hosts.yml` and set:

- `domain` - your domain name
- `secret_key` - generate with `python manage.py generate_secret_key`
- `postgres_password` - a secure password
- `admin_url` - custom admin path
- `admins` - admin email addresses
- `mailgun_api_key` - Mailgun API key (if using Mailgun for email; also add DNS records per Step 2)
- `sentry_url` - Sentry DSN (optional)

Encrypt the inventory:

```bash
cd ../../ansible
ansible-vault encrypt hosts.yml
```

## Step 4: Prepare SSH Keys

Copy public keys for all users who need server access:

```bash
cp ~/.ssh/id_rsa.pub ansible/ssh-keys/admin.pub
```

Keys must have a `.pub` extension.

## Step 5: Deploy

From the project root:

```bash
just apb site
```

This installs K3s, deploys PostgreSQL, Redis, the Django app, Traefik with SSL, and cron jobs across all nodes.

## Post-Deployment

1. Verify pods are running: `just kube get pods`
2. Run database migrations: `just rdj migrate`
3. Create a superuser: `just rdj createsuperuser`
4. Update the Site domain in Django admin

## Upgrading

- **Redeploy application**: `just apb site`
- **Update server packages**: `just apb upgrade`
- **Upgrade PostgreSQL**: see [`ansible/docs/pg_upgrade.md`](ansible/docs/pg_upgrade.md)

## Scaling

Edit `terraform/hetzner/terraform.tfvars` to add webapp nodes or upgrade server types, then run `terraform apply` and re-run Ansible.

## Redeployment After Infrastructure Rebuild

If you destroy and recreate infrastructure (`terraform destroy` / `terraform apply`):

1. Delete cached scripts with old IPs: `rm ansible/scripts/*.sh`
2. Regenerate `ansible/hosts.yml` from Terraform output
3. Re-run `just apb site`
