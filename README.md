
![coverage](/screenshots/coverage.svg?raw=True)

This is the source code for a simple, easy to use podcatcher web application. You are free to use this source to host the app yourself. A Dockerfile is provided for production deployments.

## Development

Radiofeed requires the following basic dependencies to get started:

* Python 3.12
* [uv](https://docs.astral.sh)

**Note:** if you don't have the right version of Python you can use `uv python install 3.12.x`.

For ease of local development a `docker-compose.yml` file is provided which includes Docker images:

* PostgreSQL
* Redis
* [Mailpit](https://mailpit.axllent.org/) (for local email testing)

You can use these images if you want, or use a local install of PostgreSQL or Redis.

Current tested versions are PostgreSQL 16 and Redis 7.

The [justfile](https://github.com/casey/just) has some convenient shortcuts for local development, including:

* `just install`: download and install local dependencies
* `just update`: update dependencies to latest available versions
* `just clean`: remove all non-committed files and other artifacts
* `just serve`: run the development server and Tailwind JIT compiler
* `just shell`: open a shell in the development environment
* `just test`: run unit tests
* `just check`: run unit tests and linters

The install command will also create a `.env` file with default settings for local development, if one does not already exist.

## Stack

The **Radiofeed** stack includes:

* [Django](https://djangoproject.com)
* [HTMX](https://htmx.org)
* [AlpineJS](https://alpinejs.dev)
* [Tailwind](https://tailwindcss.com)
* [PostgreSQL](https://www.postgresql.org/)

This stack was chosen for the following reasons:

1. [Locality of behavior](https://htmx.org/essays/locality-of-behaviour/): the behavior of a unit of code should be obvious from looking at the code.
2. **Performance**: reduce the burden on end-user devices and bandwidth rampant with heavy SPA frameworks
3. **Batteries included**: using popular, well-supported open source tools such as Django and PostgreSQL with a large number of features to avoid reinventing the wheel

## Deployment

The following environment variables should be set in your production installation (changing _radiofeed.app_ for your domain).

```
ALLOWED_HOSTS=radiofeed.app
DATABASE_URL=<database-url>
REDIS_URL=<redis-url>
ADMIN_URL=<admin-url>
ADMINS=me@radiofeed.app
EMAIL_HOST=mg.radiofeed.app
MAILGUN_API_KEY=<mailgun_api_key>
SECRET_KEY=<secret>
SENTRY_URL=<sentry-url>
```

Some settings such as `DATABASE_URL` may be set automatically by certain PAAS providers such as Heroku. Consult your provider documentation as required.

`EMAIL_HOST` should be set to your Mailgun sender domain along with `MAILGUN_API_KEY` if you are using Mailgun.

You should ensure the `SECRET_KEY` is sufficiently random: run the `generate_secret_key` custom Django command to create a suitable random string.

In some server configurations your load balancer (e.g. Nginx) may set the `strict-transport-security` headers by default. If not, you can set the environment variable `USE_HSTS=true`.

In production it's also a good idea to set `ADMIN_URL` to something other than the default _admin/_. Make sure it ends in a forward slash, e.g. _some-random-path/_.

A Dockerfile is provided for standard container deployments which should also work on Heroku or another PAAS.

Once you have access to the Django Admin, you should configure the default Site instance with the correct production name and domain.

The `ansible` directory contains full Playbooks for a multi-server deployment to a shared hosting provider such as Hetzner or Digital Ocean, this can be copied and modified for your particular use-case.

### Deployment with Hetzner

A full deployment guide for Hetzner Cloud is available. You should have a DNS domain set up using e.g. Hetzner DNS or Cloudflare.

1. [Create a new Hetzner Cloud project](https://docs.hetzner.com/cloud/)
2. Go to Security > API Tokens and create a new token with read/write access
3. Copy the token and add it to your environment as `HCLOUD_TOKEN`
4. Run `terraform -chdir=tf init` to download the Hetzner provider
5. Run `terraform -chdir=rf apply -var hcloud_token=$HCLOUD_TOKEN` to create the necessary resources
6. Change to the `ansible` directory and use `ansible-vault create hosts` to create a new inventory file and add the IP addresses of all the servers
7. Do the same for `vars/django.yml`, `vars/postgres.yml`, and `vars/site.yml` to create the necessary variables (see example vars files for guidance)
8. Run `ansible-playbook -i hosts site.yml` to deploy the application
9. In your DNS configuration, point your domain to the new load balancer IP address

### Scheduling background tasks

In production you should set up the following cron jobs to run these Django commands (with suggested schedules and arguments):

#### Parse podcast RSS feeds:

```bash
*/6 * * * * python manage.py parse_feeds
```

#### Generate similar recommendations for each podcast:

```bash
15 6 * * * python manage.py create_recommendations
```

#### Send podcast recommendations to users:

```bash
15 9 * * 1 python manage.py send_recommendations_emails
```

**Note:** ansible will set up these cron jobs for you if you use the provided Playbooks.
