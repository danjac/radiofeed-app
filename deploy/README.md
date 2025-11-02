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

1. Ensure you have access to a Radiofeed Docker image. The default image is `ghcr.io/danjac/radiofeed-app`. If this image is not available, you will need to build and push it yourself to a container registry.

2. Run `just apb site` in the project root directory to deploy to your servers.

## Upgrading

To update server dependencies, run `just apb upgrade`.

## Upgrading PostgreSQL

To upgrade PostgreSQL to a new major version, follow these steps:

1. In the `hosts.yml` file, add the new postgres version as `postgres_new_image` and the new data volume as `postgres_new_volume`.
2. Ensure the new volume exists on the server.
3. Run `just apb deploy`. This will create a new PostgreSQL container with the new version and migrate the data as `postgres-upgrade`.
3. SSH into the server node.
4. Verify that the new PostgreSQL container is running correctly.
5. Delete the deployments and cronjobs:

   ```bash
   kubectl delete deployment django-app
   kubectl delete cronjobs -l app=django-cronjobs
   ```
6. SSH into the server node and run the `./pg_upgrade.sh` script located in the home directory (assuming current postgres is `postgres-0` and new is `postgres-upgrade-0`: check and adjust as necessary):

   ```bash
   sudo bash ~/pg_upgrade.sh posgres-0 postgres-upgrade-0
   ```
7. Once the upgrade is complete, update the `hosts.yml` file to set `postgres_image` to the new version and `postgres_volume` to the new volume.
8. Run `just apb deploy` again to redeploy the Django application and cronjobs with the upgraded PostgreSQL database.
9. Verify that the application is functioning correctly with the new PostgreSQL version, and delete the old PostgreSQL deployment and volume if everything is working as expected.
