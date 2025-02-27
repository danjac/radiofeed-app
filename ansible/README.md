Ansible playbooks for deploying [Radiofeed](https://github.com/danjac/radiofeed-app)

## Architecture

The architecture can run on cheap VM hosting e.g. Hetzner or Digital Ocean droplets. It assumes the following:

1. One server running PostgreSQL and Redis.
2. One server running cron jobs and managing Docker swarm.
3. Multiple Docker swarm workers running a Gunicorn/Django instance.

It is assumed you are deploying the app servers behind a load balancer. It is recommended to use one provided by your host e.g. from [Hetzner](https://www.hetzner.com/cloud/load-balancer/) or use e.g Nginx or Traefik.

The Ansible playbooks will deploy all of the above using [K3s](https://www.rancher.com/products/k3s).

## Setup

1. Copy the following file `hosts.yml.example` to `hosts.yml`
2. Edit file as required, adding your server-specific settings.
3. Encrypt the `hosts.yml` file using `ansible-vault` and make backups to a secure place.

## Deployment

For ease of use, a [justfile](https://github.com/casey/just) has been provided for running the Ansible playbooks.

You should have root SSH access to your servers.

1. Ensure you have access to a Radiofeed Docker image. The default image is `ghcr.io/danjac/radiofeed-app`.

2. Run `just deploy` to deploy to your servers.

## Upgrade

To update server dependencies, run `just pb upgrade`.

## Django management commands

Run `just pb dj_manage` to generate a `manage.sh` script in the local `ansible` directory. This will run Django management commands in the cron scheduler server:

```bash
just djmanage # run once to create the bash script

./manage.sh migrate --check
```
