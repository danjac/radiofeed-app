Ansible playbooks for deploying [Radiofeed](https://github.com/danjac/radiofeed-app)

## Architecture

The architecture can run on cheap VM hosting e.g. Hetzner or Digital Ocean droplets. It runs the Django web application, PostgreSQL database, Redis cache, and cronjobs in a [K3s](https://www.rancher.com/products/k3s) cluster.

It is assumed you are deploying the app servers behind a load balancer. It is recommended to use one provided by your host e.g. from [Hetzner](https://www.hetzner.com/cloud/load-balancer/) or use e.g Nginx or Traefik.

## Setup

1. Copy the following file `hosts.yml.example` to `hosts.yml`
2. Edit file as required, adding your server-specific settings.
3. Encrypt the `hosts.yml` file using `ansible-vault` and make backups to a secure place.

## Deployment

For ease of use, a [justfile](https://github.com/casey/just) has been provided for running the Ansible playbooks.

You should have root SSH access to your servers.

1. Ensure you have access to a Radiofeed Docker image. The default image is `ghcr.io/danjac/radiofeed-app`.

2. Run `just pb site` to deploy to your servers.

## Upgrade

To update server dependencies, run `just pb upgrade`.

## Django management commands

Run `just pb dj_manage` to generate a `manage.sh` script in the local `ansible` directory. This will run Django management commands in the cron scheduler server:

```bash
just djmanage # run once to create the bash script

./manage.sh migrate --check
```

## Database commands

Run `just pb psql` to generate a Psql script in the local `ansible` directory. This will allow you to access PostgreSQL on the database server.

## Kubectl commands

Run `just pb kubectl` to generate a Kubectl script in the local `ansible` directory. This will allow you to access the K3s cluster.

```
just kubectl get pods
```
