# Ansible Deployment for Radiofeed K3s Cluster

This directory contains Ansible playbooks for deploying Radiofeed to a K3s (lightweight Kubernetes) cluster. The deployment includes the Django web application, PostgreSQL database, Redis cache, and scheduled cron jobs.

## Architecture Overview

The K3s cluster consists of:

- **1 Server Node**: K3s control plane + Traefik ingress controller (load balancer)
- **1 Database Node**: PostgreSQL 16 + Redis 8
- **1 Job Runner Node**: Runs scheduled tasks (feed parsing, notifications, recommendations)
- **N Web App Nodes**: Django application containers (default: 2, horizontally scalable)

All nodes communicate via a private network for security. The server node exposes ports 80 (HTTP) and 443 (HTTPS) to the internet via Cloudflare.

### Technology Stack

- **K3s**: Lightweight Kubernetes distribution
- **Traefik**: Ingress controller and load balancer
- **PostgreSQL 16**: Primary database with persistent volume
- **Redis 8**: Caching and session storage
- **Cloudflare**: CDN, SSL/TLS termination, and DDoS protection

## Prerequisites

### 1. Infrastructure

**Option A: Terraform (Recommended)**

Use the provided Terraform configurations to provision infrastructure:

```bash
# Provision Hetzner servers
cd terraform/hetzner
terraform apply

# Configure Cloudflare CDN + SSL
cd ../cloudflare
terraform apply

# Generate Ansible inventory
cd ../hetzner
terraform output -raw ansible_inventory > ../../ansible/hosts.yml
```

See [`../terraform/hetzner/README.md`](../terraform/hetzner/README.md) and [`../terraform/cloudflare/README.md`](../terraform/cloudflare/README.md) for details.

**Option B: Manual Infrastructure**

If you have existing servers or use a different provider:

- **Servers**: 4+ Ubuntu 24.04 servers with root SSH access
- **Network**: Private network between all nodes (recommended)
- **Firewall**: Server node open to ports 22, 80, 443; other nodes open to port 22
- **DNS**: A record pointing to the server node public IP
- **Storage**: Volume attached to database node for PostgreSQL data

### 2. Cloudflare Origin Certificates

**Required:** Cloudflare origin certificates for SSL/TLS between Cloudflare and your origin server.

Generate certificates:

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Select your domain → **SSL/TLS** → **Origin Server**
3. Click **Create Certificate**
4. Select:
   - **Generate private key and CSR with Cloudflare**
   - Validity: **15 years** (recommended)
   - Hostnames: Your domain and wildcards (e.g., `example.com`, `*.example.com`)
5. Click **Create**
6. Save the files:
   - **Origin Certificate** → `ansible/certs/cloudflare.pem`
   - **Private Key** → `ansible/certs/cloudflare.key`

Create the certs directory if it doesn't exist:

```bash
mkdir -p ansible/certs
chmod 700 ansible/certs
chmod 600 ansible/certs/cloudflare.*
```

**Security Note:** Never commit these certificates to version control. Add `ansible/certs/` to `.gitignore`.

### 3. SSH Public Keys

Add SSH public keys for all users who need server access:

```bash
mkdir -p ansible/ssh-keys

# Copy your public key
cp ~/.ssh/id_rsa.pub ansible/ssh-keys/admin.pub

# Add more users
cp ~/teammate-key.pub ansible/ssh-keys/teammate.pub
```

**Important:** Keys must have `.pub` extension.

### 4. Docker Image

You need a Docker image of the Radiofeed application pushed to a container registry.

**Option A: Use GitHub Container Registry (Recommended)**

If you have a GitHub repository with GitHub Actions:

1. The workflow in `.github/workflows/docker.yml` builds and pushes images
2. Images are tagged with commit SHA: `ghcr.io/username/radiofeed:abc123def456`
3. Find the latest image SHA in GitHub Actions → Docker workflow → "Set image output"

**Option B: Build and Push Manually**

```bash
# Build the image
docker build -t ghcr.io/username/radiofeed:v1.0.0 .

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u username --password-stdin

# Push the image
docker push ghcr.io/username/radiofeed:v1.0.0
```

**Important:** Always use a pinned image tag (SHA or version), not `:latest` or `:main`.

### 5. Ansible Requirements

Install Ansible and required collections:

```bash
# Install Ansible (if not already installed)
pip install ansible

# Install required collections
ansible-galaxy install -r ansible/requirements.yml
```

### 6. Django Secret Key

Generate a secure secret key:

```bash
python manage.py generate_secret_key
```

Save this key for the inventory configuration.

## Configuration

### 1. Create Inventory File

**Option A: From Terraform (Recommended)**

```bash
cd terraform/hetzner
terraform output -raw ansible_inventory > ../../ansible/hosts.yml
```

**Option B: Manual Configuration**

```bash
cd ansible
cp hosts.yml.example hosts.yml
```

Edit `hosts.yml` with your server IPs.

### 2. Configure Variables

Edit `ansible/hosts.yml` and update the `vars` section:

#### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `domain` | Your domain name | `"radiofeed.app"` |
| `secret_key` | Django secret key (generate with `manage.py generate_secret_key`) | `"long-random-string"` |
| `postgres_password` | PostgreSQL password (use strong password) | `"secure-password-here"` |
| `admin_url` | Custom admin URL path (security through obscurity) | `"my-secret-admin/"` |
| `admins` | Admin email addresses (comma-separated) | `"admin@example.com"` |
| `contact_email` | Contact email for the app | `"contact@example.com"` |

#### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `postgres_volume` | Volume ID/path for PostgreSQL data | `""` (Terraform provides this) |
| `secret_key_fallbacks` | Old secret keys for rotation (comma-separated) | `""` |
| `mailgun_api_key` | Mailgun API key for email sending | `""` |
| `mailgun_api_url` | Mailgun API URL (US or EU) | `"https://api.eu.mailgun.net/v3"` |
| `sentry_url` | Sentry DSN for error tracking | `""` |
| `pwa_sha256_fingerprints` | SHA256 fingerprints for PWA (advanced) | `""` |
| `cron_schedules_override` | Override default cron schedules | (see example below) |

#### Example Configuration

```yaml
vars:
  domain: "radiofeed.app"
  admin_url: "secret-admin-path/"
  admins: "admin@radiofeed.app,ops@radiofeed.app"
  contact_email: "hello@radiofeed.app"

  # Security
  secret_key: "django-insecure-CHANGE-THIS-TO-RANDOM-STRING" # gitleaks:allow
  secret_key_fallbacks: "" # gitleaks:allow

  # Database
  postgres_password: "very-secure-password-here" # gitleaks:allow
  postgres_volume: "/dev/disk/by-id/scsi-0HC_Volume_12345678"

  # Email (optional - required for notifications)
  mailgun_api_key: "key-abc123def456" # gitleaks:allow
  mailgun_api_url: "https://api.eu.mailgun.net/v3"

  # Monitoring (optional)
  sentry_url: "https://abc123@o123456.ingest.us.sentry.io/7654321" # gitleaks:allow

  # PWA (optional - for advanced users)
  pwa_sha256_fingerprints: ""

  # Override cron schedules (optional)
  # cron_schedules_override:
  #   parse_feeds: "*/30 * * * *"  # Every 30 minutes instead of default
  #   send_notifications: "0 10 * * *"  # 10 AM daily
```

### 3. Update Docker Image

Edit `ansible/group_vars/all.yml` and set the Docker image to a **pinned version**:

```yaml
docker_image: "ghcr.io/username/radiofeed:abc123def456"
```

**Important:** Replace `abc123def456` with the actual commit SHA from your GitHub Actions build, or use a semantic version like `v1.0.0`. Never use `:main` or `:latest` in production.

To find the latest image SHA:
- Go to GitHub Actions → Select the latest successful Docker workflow run
- Look for "Set image output" step
- Copy the full image name with SHA

### 4. Encrypt Sensitive Data (Recommended)

Encrypt the inventory file with Ansible Vault:

```bash
cd ansible
ansible-vault encrypt hosts.yml
```

Set a strong vault password and store it securely (password manager recommended).

**Backup:** Make encrypted backups of `hosts.yml` to a secure location.

## Deployment

### Initial Deployment

From the project root directory:

```bash
just apb site
```

If you encrypted `hosts.yml` with Ansible Vault:

```bash
ansible-playbook -i ansible/hosts.yml ansible/site.yml --ask-vault-pass
```

### What Happens During Deployment

The `site.yml` playbook performs the following steps:

1. **Create deployment user** (`ubuntu` by default)
2. **Install prerequisites**:
   - System packages (curl, git, etc.)
   - Docker
   - K3s dependencies
3. **Set up K3s cluster**:
   - Install K3s server on the server node
   - Join agent nodes to the cluster
   - Label nodes with roles (database, jobrunner, webapp)
4. **Deploy application**:
   - Create Kubernetes secrets (Django secret key, PostgreSQL password)
   - Deploy PostgreSQL StatefulSet with persistent volume
   - Deploy Redis Deployment
   - Deploy Django web application
   - Create Traefik IngressRoute with SSL/TLS
   - Set up cron jobs for feed parsing and notifications
5. **Generate helper scripts**:
   - `ansible/scripts/kubectl.sh` - Run kubectl commands
   - `ansible/scripts/psql.sh` - Access PostgreSQL
   - `ansible/scripts/manage.sh` - Run Django management commands

Deployment takes approximately 10-15 minutes depending on server specs and network speed.

### Post-Deployment

After deployment completes:

1. **Verify services are running**:
   ```bash
   ansible/scripts/kubectl.sh get pods
   ```

   All pods should show `Running` status.

2. **Run database migrations**:
   ```bash
   ansible/scripts/manage.sh dj_manage migrate
   ```

3. **Create superuser**:
   ```bash
   ansible/scripts/manage.sh dj_manage createsuperuser
   ```

4. **Update Site in Django admin**:
   - Visit `https://yourdomain.com/your-admin-url/`
   - Go to Sites → Change the default site
   - Set domain name and display name

5. **Test the application**:
   - Visit `https://yourdomain.com`
   - Verify static assets load (check browser DevTools → Network)
   - Check Cloudflare caching headers

## Available Playbooks

| Playbook | Command | Description |
|----------|---------|-------------|
| `site.yml` | `just apb site` | Complete deployment (initial setup) |
| `deploy.yml` | `just apb deploy` | Update application only (new Docker image) |
| `crons.yml` | `just apb crons` | Update cron job schedules |
| `upgrade.yml` | `just apb upgrade` | Upgrade system packages on all servers |
| `users.yml` | `just apb users` | Update SSH keys for users |
| `pg_upgrade.yml` | `just apb pg_upgrade` | Upgrade PostgreSQL version |

## Common Operations

### Update Application

When you have a new Docker image:

1. **Update image tag** in `ansible/group_vars/all.yml`:
   ```yaml
   docker_image: "ghcr.io/username/radiofeed:new-sha-here"
   ```

2. **Deploy update**:
   ```bash
   just apb deploy
   ```

3. **Run migrations** (if any):
   ```bash
   ansible/scripts/manage.sh dj_manage migrate
   ```

4. **Verify deployment**:
   ```bash
   ansible/scripts/kubectl.sh get pods
   ansible/scripts/kubectl.sh rollout status deployment/radiofeed-web
   ```

### Run Django Management Commands

```bash
# Run migrations
ansible/scripts/manage.sh dj_manage migrate

# Create superuser
ansible/scripts/manage.sh dj_manage createsuperuser

# Run custom management commands
ansible/scripts/manage.sh dj_manage parse_feeds --limit 100
ansible/scripts/manage.sh dj_manage send_notifications
```

### Access PostgreSQL

```bash
# Connect to PostgreSQL
ansible/scripts/psql.sh psql -U postgres radiofeed

# Backup database
ansible/scripts/psql.sh pg_dump -U postgres radiofeed > backup.sql

# Restore database
ansible/scripts/psql.sh psql -U postgres radiofeed < backup.sql
```

### Use kubectl

```bash
# Get all pods
ansible/scripts/kubectl.sh get pods

# Check logs
ansible/scripts/kubectl.sh logs -f deployment/radiofeed-web

# Get pod details
ansible/scripts/kubectl.sh describe pod radiofeed-web-xxx

# Port forward (for debugging)
ansible/scripts/kubectl.sh port-forward deployment/radiofeed-web 8000:8000
```

### Update SSH Keys

1. Add/remove keys in `ansible/ssh-keys/`
2. Run: `just apb users`

### Update Cron Schedules

1. Edit `ansible/hosts.yml` and add `cron_schedules_override`:
   ```yaml
   vars:
     cron_schedules_override:
       parse_feeds: "*/30 * * * *"  # Every 30 minutes
       send_notifications: "0 9 * * *"  # 9 AM daily
   ```

2. Apply changes:
   ```bash
   just apb crons
   ```

### Upgrade System Packages

Update all servers:

```bash
just apb upgrade
```

This updates system packages and reboots servers if necessary.

## Monitoring and Troubleshooting

### Check Service Status

```bash
# All pods
ansible/scripts/kubectl.sh get pods

# Specific services
ansible/scripts/kubectl.sh get deployment
ansible/scripts/kubectl.sh get statefulset
ansible/scripts/kubectl.sh get cronjob
```

### View Logs

```bash
# Web application logs
ansible/scripts/kubectl.sh logs -f deployment/radiofeed-web

# Cron job logs
ansible/scripts/kubectl.sh logs -f cronjob/radiofeed-parse-feeds

# PostgreSQL logs
ansible/scripts/kubectl.sh logs -f statefulset/postgres
```

### Common Issues

#### Pods not starting

**Problem**: Pods stuck in `Pending` or `CrashLoopBackOff` state.

**Solutions**:
```bash
# Check pod details
ansible/scripts/kubectl.sh describe pod <pod-name>

# Check logs
ansible/scripts/kubectl.sh logs <pod-name>

# Check node resources
ansible/scripts/kubectl.sh top nodes

# Verify secrets exist
ansible/scripts/kubectl.sh get secrets
```

#### SSL/TLS errors

**Problem**: HTTPS not working or certificate errors.

**Checklist**:
- Cloudflare origin certificates exist in `ansible/certs/`
- Certificates deployed: `ansible/scripts/kubectl.sh get secret cloudflare-origin-cert`
- Cloudflare SSL mode set to "Full" (not "Full (strict)")
- DNS pointing to correct server IP
- Firewall allows ports 80 and 443

#### Database connection errors

**Problem**: Application can't connect to PostgreSQL.

**Solutions**:
```bash
# Check PostgreSQL pod
ansible/scripts/kubectl.sh get pods -l app=postgres

# Test connection
ansible/scripts/psql.sh psql -U postgres -c "SELECT 1"

# Check PostgreSQL logs
ansible/scripts/kubectl.sh logs statefulset/postgres
```

#### Cron jobs not running

**Problem**: Feed parsing or notifications not working.

**Solutions**:
```bash
# Check cron job status
ansible/scripts/kubectl.sh get cronjobs

# Check recent job runs
ansible/scripts/kubectl.sh get jobs

# Check cron job logs
ansible/scripts/kubectl.sh logs -f job/<job-name>

# Manually trigger a job
ansible/scripts/kubectl.sh create job --from=cronjob/radiofeed-parse-feeds test-run
```

## Scaling

### Add More Web Application Nodes

1. **Provision new server** (via Terraform or manually)
2. **Add to inventory** in `ansible/hosts.yml`:
   ```yaml
   agents:
     hosts:
       # ... existing hosts ...
       123.456.78.915:
         hostname: webapp-3
         role: webapp
   ```
3. **Run deployment**:
   ```bash
   just apb site
   ```

The new node will join the cluster and start serving traffic automatically.

### Increase Web Application Replicas

Edit K3s deployment to increase replicas (handled automatically based on number of webapp nodes).

## Backup and Recovery

### Database Backups

The deployment includes automated PostgreSQL backups. See `docs/pg_upgrade.md` for details.

Manual backup:

```bash
# Create backup
ansible/scripts/psql.sh pg_dump -U postgres -Fc radiofeed > radiofeed-$(date +%Y%m%d).dump

# Restore backup
ansible/scripts/psql.sh pg_restore -U postgres -d radiofeed radiofeed-20260203.dump
```

### Configuration Backups

Always keep encrypted backups of:
- `ansible/hosts.yml` (encrypted with Ansible Vault)
- `ansible/certs/cloudflare.pem` and `cloudflare.key`
- `ansible/ssh-keys/`

## Upgrading PostgreSQL

See [docs/pg_upgrade.md](docs/pg_upgrade.md) for detailed instructions on upgrading PostgreSQL versions.

## Security Best Practices

1. **Encrypt inventory**: Use `ansible-vault encrypt hosts.yml`
2. **Rotate secrets**: Update `secret_key` and add old one to `secret_key_fallbacks`
3. **Strong passwords**: Use long, random passwords for `postgres_password`
4. **Custom admin URL**: Set `admin_url` to something non-obvious
5. **SSH keys**: Remove access for users who leave the team
6. **Firewall**: Only server node should be publicly accessible
7. **Updates**: Regularly run `just apb upgrade` for security patches
8. **Monitoring**: Set up Sentry for error tracking

## Resources

- [K3s Documentation](https://docs.k3s.io/)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Ansible Documentation](https://docs.ansible.com/)
- [Hetzner Terraform Setup](../terraform/hetzner/README.md)
- [Cloudflare Terraform Setup](../terraform/cloudflare/README.md)

## Support

For issues:
- **Infrastructure**: See `../terraform/hetzner/README.md`
- **Cloudflare**: See `../terraform/cloudflare/README.md`
- **Application**: See project root `README.md`
- **PostgreSQL Upgrade**: See `docs/pg_upgrade.md`
