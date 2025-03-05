Ansible playbooks for deploying [Radiofeed](https://github.com/danjac/radiofeed-app)

## Architecture

The architecture can run on cheap VM hosting e.g. Hetzner or Digital Ocean droplets. It runs the Django web application, PostgreSQL database, Redis cache, and cronjobs in a [K3s](https://www.rancher.com/products/k3s) cluster.

It is assumed you are deploying the app servers behind a load balancer. It is recommended to use one provided by your host e.g. from [Hetzner](https://www.hetzner.com/cloud/load-balancer/) or use e.g Nginx or Traefik.

## Setup

1. Copy the following file `hosts.yml.example` to `hosts.yml`
2. Edit file as required, adding your server-specific settings.
3. Encrypt the `hosts.yml` file using `ansible-vault` and make backups to a secure place.

To handle reverse proxy from your load balancer, ensure the LB points to the app servers on the correct port. This is set in inventory file setting `django_port`, for example `30081`.

## Deployment

For ease of use, a [justfile](https://github.com/casey/just) has been provided for running the Ansible playbooks.

You should have root SSH access to your servers.

1. Ensure you have access to a Radiofeed Docker image. The default image is `ghcr.io/danjac/radiofeed-app`.

2. Run `just pb site` to deploy to your servers.

## Upgrade

To update server dependencies, run `just pb upgrade`.
