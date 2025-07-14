Ansible playbooks for deploying [Radiofeed](https://github.com/danjac/radiofeed-app)

## Architecture

The architecture can run on cheap VM hosting e.g. Hetzner or Digital Ocean droplets. It runs the Django web application, PostgreSQL database, Redis cache, and cronjobs in a [K3s](https://www.rancher.com/products/k3s) cluster. It assumes you are using Cloudflare for DNS and caching.

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

2. Run `just pb site` to deploy to your servers.

## Upgrade

To update server dependencies, run `just pb upgrade`.
