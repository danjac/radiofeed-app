This is the source code for a [simple, easy to use podcatcher web application](https://radiofeed.app). You are free to use this source to host the app yourself. The application is intended to be run in production in Heroku or a Heroku-like PAAS such as Dokku or Railway; however it should be quite easy to adapt it to run in other environments such as AWS EC2.

![desktop](/screenshots/desktop.png?raw=True)

## Development

Radiofeed requires the following basic dependencies to get started:

* Python 3.10+
* Node 16+
* [Poetry](https://github.com/python-poetry/poetry)

For ease of local development a `docker-compose.yml` is provided which includes:

* PostgreSQL
* Redis
* Mailhog (for local email testing and development)

You can use these images if you want, or use a local install of PostgreSQL or Redis.

If you want to use the Docker images just run:

```bash
docker-compose up --build -d
```

Current tested versions are PostgreSQL 14+ and Redis 6.2+.

Next copy `.env.example` to `.env`. The default settings should work with the Docker services provided, otherwise modify as needed, in particular `DATABASE_URL` and `REDIS_URL`.

You should run your development environment inside a virtualenv e.g.:

```bash
python -m venv .venv && source .venv/bin/activate
```

Poetry should create the virtualenv for you automatically.

The `Makefile` has some convenient shortcuts for local development, including:

* `make install`: download and install front and backend dependencies
* `make dbinstall`: run migrations and install sample fixtures
* `make test`: run unit tests
* `make update`: update all front and backend dependencies to latest available versions
* `make watch`: compile JavaScript and CSS assets on the fly
* `make serve`: run Django development server (on 127.0.0.1:8000)
* `make shell`: run Django shell on iPython

## Deployment

The following environment variables should be set in your production installation (changing `radiofeed.app` for your domain).

```
ALLOWED_HOSTS=radiofeed.app
CONN_MAX_AGE=360
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

A Dockerfile is provided for standard container deployments e.g. on Dokku.

Once you have access to the Django Admin, you should configure the default Site instance with the correct production name and domain.

### Crons

In production you should set up the following cron jobs to run these Django commands (with suggested schedules and arguments):

Parse podcast RSS feeds:

```bash
*/6 * * * * python manage.py parse_feeds
```

You can also run this command continuously using the `--watch` flag:

```bash
python manage.py parse_feeds --watch
```

Generate similar recommendations for each podcast:

```bash
15 6 * * * python manage.py create_recommendations
```

Send podcast recommendations to users:

```bash
15 9 * * 1 python manage.py send_recommendations_emails
```

An `app.json` configuration with these cron schedules is included for Dokku deployment.
