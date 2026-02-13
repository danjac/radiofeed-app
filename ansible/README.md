This directory contains Ansible playbooks for deploying [Radiofeed](https://github.com/danjac/radiofeed-app) to a K3s cluster.

## Architecture

The architecture can run on cheap VM hosting e.g. Hetzner or Digital Ocean droplets. It runs the Django web application, PostgreSQL database, Redis cache, and cronjobs in a [K3s](https://www.rancher.com/products/k3s) cluster. It assumes you are using Cloudflare for DNS and caching. Traefik is used as the ingress controller for load-balancing.

## Setup

1. Copy the following file `hosts.yml.example` to `hosts.yml`
2. Edit file as required, adding your server-specific settings.
3. Encrypt the `hosts.yml` file using `ansible-vault` and make backups to a secure place.
4. Copy the origin certificates from your Cloudflare account to the `certs` directory. They should be called `cloudflare.pem` and `cloudflare.key`.
5. Ensure your Cloudflare `A` record etc. points to the **server** node public IP address.
6. Add SSH pub keys to `ssh-keys` (must have `.pub` extension) for all users who should have access.

## Deployment

For ease of use, a [justfile](https://github.com/casey/just) has been provided for running the Ansible playbooks.

You should have root SSH access to your servers.

1. Ensure you have access to a Radiofeed Docker image. The default image is `ghcr.io/danjac/radiofeed-app:main`. If this image is not available, you will need to build and push it yourself to a container registry.

2. Run `just apb site` in the project root directory to deploy to your servers.

### Post-deployment steps

After the initial deployment completes:

1. Verify all pods are up and running: `just kube get pods`
2. Run database migrations: `just rdj migrate`

### Redeployment notes

If you are redeploying after rebuilding infrastructure (e.g. after `terraform destroy` and `terraform apply`):

1. Delete the generated local scripts before redeploying, as they contain hardcoded IPs from the previous infrastructure:
   ```bash
   rm ansible/scripts/*.sh
   ```
2. If the k3s server fails to start with `address already in use`, kill any leftover k3s processes on the server before re-running the playbook:
   ```bash
   ssh ubuntu@<server-ip> "sudo k3s-killall.sh"
   ```
3. If a PersistentVolume needs its `hostPath` changed, you must delete the existing PV and PVC first (the `persistentvolumesource` is immutable after creation):
   ```bash
   just kube delete pv <pv-name>
   just kube delete pvc <pvc-name>
   ```
4. If a node shows `NotReady` with a `CIDRAssignmentFailed` event after deployment, restart the k3s agent on that node:
   ```bash
   ssh ubuntu@<node-public-ip> "sudo systemctl restart k3s-agent"
   ```
   Verify with `just kube get nodes`.

## Upgrading

To update server dependencies, run `just apb upgrade`.

## Upgrading PostgreSQL

To upgrade PostgreSQL see [these instructions](docs/pg_upgrade.md).
