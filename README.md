
![coverage](/screenshots/coverage.svg?raw=True)

This is the source code for a simple, easy to use podcatcher web application. You are free to use this source to host the app yourself. A Dockerfile is provided for production deployments.

## Development

Radiofeed requires the following basic dependencies to get started:

* Python 3.14
* [uv](https://docs.astral.sh)

**Note:** if you don't have the right version of Python you can use `uv python install 3.14.x`.

For ease of local development a `docker-compose.yml` file is provided which includes Docker images:

* PostgreSQL
* Redis
* [Mailpit](https://mailpit.axllent.org/) (for local email testing)

You can use these images if you want, or use a local install of PostgreSQL or Redis.

Current tested versions are PostgreSQL 17 and Redis 8.

The [justfile](https://github.com/casey/just) has some convenient shortcuts for local development, including:

* `just install`: download and install local dependencies
* `just update`: update dependencies to latest available versions
* `just serve`: run the development server and Tailwind JIT compiler
* `just dj [command]`: run Django management commands
* `just test`: run unit tests
* `just start` and `just start`: start/stop Docker dev containers

Run `just` to see all available commands.

**NOTE**: Default settings provided should be suitable for local development, but if you are not using the Docker images you may need to adjust database connection and other settings by creating a `.env` file in the project root.

## Stack

The **Radiofeed** stack includes:

* [Django](https://djangoproject.com)
* [HTMX](https://htmx.org)
* [AlpineJS](https://alpinejs.dev)
* [Tailwind](https://tailwindcss.com)
* [PostgreSQL](https://www.postgresql.org/)

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

The `ansible` directory contains full Playbooks for a multi-server [K3s](https://www.rancher.com/products/k3s) deployment to a shared hosting provider such as Hetzner or Digital Ocean, this can be copied and modified for your particular use-case.
