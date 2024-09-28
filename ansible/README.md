Ansible playbooks for deploying [Radiofeed](https://github.com/danjac/radiofeed-app)

## Architecture

The architecture can run on cheap VM hosting e.g. Hetzner or Digital Ocean droplets. It assumes the following:

1. One server running PostgreSQL and Redis.
2. One server running cron jobs and other processes.
3. One or more app servers running a Django application behind Gunicorn.

It is assumed you are deploying the app servers behind a load balancer. It is recommended to use one provided by your host e.g. from [Hetzner](https://www.hetzner.com/cloud/load-balancer/).

The Ansible playbooks will deploy all of the above using Docker images.

## Setup

1. Copy the following files:

    * `hosts.example` > `hosts`
    * `vars/django.yml.example` > `vars/django.yml`
    * `vars/site.yml.example` > `vars/site.yml`
    * `vars/postgresql.yml.example` > `vars/postgresql.yml`

2. Edit the above files as required, adding your server-specific settings.
3. Encrypt the vars files using `ansible-vault` and make backups to a secure place e.g. [Bitwarden](https://bitwarden.com/).

## Deployment

1. Ensure you have access to a Radiofeed Docker image. The default image is `danjac2018/radiofeed:latest`.

2. Run `ansible-playbook -v -i ./hosts ./site.yml` to deploy to your servers.

## Upgrade

To update server dependencies, run `ansible-playbook -v -i ./hosts ./upgrade.yml`.

## Django management commands

Run `ansible-playbook -v -i ./hosts ./manage.yml` to generate a `manage.sh` script in the `ansible` directory. This will run Django management commands in the cron scheduler server:

```bash
ansible-playbook -v -i ./hosts ./manage.yml # run once

./manage.sh migrate --check
```
