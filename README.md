This is the source code for a [simple, easy to use podcatcher web application](https://radiofeed.app). You are free to use this source to host the app yourself. The application is intended to be run in production in Heroku or a Heroku-like PAAS such as Dokku or Railway; however it should be quite easy to adapt it to run in other environments such as AWS EC2.

![desktop](/screenshots/desktop.png?raw=True)

## Running Radiofeed on your local machine

Radiofeed requires the following dependencies:

* Python 3.10+
* Node 16+
* Poetry

### Additional requirements

For ease of local development a `docker-compose.yml` is provided which includes:

* PostgreSQL
* Redis
* Mailhog (for local email testing and development)

Just run `docker-compose`:

```bash
docker-compose build && docker-compose up -d
```

You can use these images if you want, or use a local install of PostgreSQL or Redis.

Current tested versions are PostgresSQL 14+ and Redis 6.2+.

### Django setup


Copy `.env.example` to `.env`.

The default settings should just work as-is with the services provided with the `docker-compose.yml` file. If you are using local instances of PostgreSQL, Redis, etc then change these settings accordingly.

To install dependencies for local development:

```bash
poetry install
```

Install the NLTK corpora:

```bash
xargs python -m nltk.downloader <./nltk.txt
```

Run database migrations:

```bash
python manage.py migrate
```

You can also install default iTunes categories and a selection of popular podcasts from fixtures:

```bash
python manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz

python manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz
```

This should provide some useful data to get started with. You can run the `parse_feeds` command detailed below to sync podcasts with their RSS feeds.

Finally, as with any Django project, you should also create a super-user to access the admin section:

```bash
python manage.py createsuperuser
```


### Frontend setup

To install frontend dependencies just run `npm ci`.

### Running development environment

The easiest way to spin up your local development environment is to run the `bootstrap.sh` script. This uses [Honcho](https://honcho.readthedocs.io/), which is included as a local dependency:

```bash
./bootstrap.sh
```

This will start up:

* Django development server
* `tailwindcss` and `esbuild` for building frontend assets on the fly

Tests can be run with `pytest`:

```bash
python -m pytest
```

## Deployment

The following environment variables should be set in your production installation (changing `radiofeed.app` for your domain).

```
DJANGO_SETTINGS_MODULE=radiofeed.settings.production
DOMAIN_NAME=radiofeed.app
DATABASE_URL=<database-url>
REDIS_URL=<redis-url>
ADMIN_URL=<admin-url>
ADMINS=me@radiofeed.app
EMAIL_HOST=mg.radiofeed.app
MAILGUN_API_KEY=<mailgun_api_key>
SECRET_KEY=<secret>
SENTRY_URL=<sentry-url>
CONTACT_EMAIL=admin@radiofeed.app
```

Some settings such as `DATABASE_URL` may be set automatically by certain PAAS providers such as Heroku. Consult your provider documentation as required.

`EMAIL_HOST` should be set to your Mailgun sender domain along with `MAILGUN_API_KEY` if you are using Mailgun.

You should ensure the `SECRET_KEY` is sufficiently random: run the `generate_secret_key` custom Django command to create a suitable random string.

By default `ALLOWED_HOSTS` will be set to the same value as your `DOMAIN_NAME`. If you should require a different list of hosts, set the `ALLOWED_HOSTS` environment variable as a comma-separated list.

In production it's also a good idea to set `ADMIN_URL` to something other than the default _admin/_. Make sure it ends in a forward slash, e.g. _some-random-path/_.

A `Procfile` is provided for Heroku-like deployments (including Dokku, Railway etc).

Once you have access to the Django Admin, you should configure the default Site instance with the correct production name and domain.

### Crons

In production you should set up the following cron jobs to run these Django commands (with suggested schedules and arguments):

Parse podcast RSS feeds:

```bash
*/6 * * * * python manage.py parse_feeds
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

### Updating dependencies

To update backend, frontend and development dependencies, just run the `upgrade.sh` script:

```bash
./upgrade.sh
```

After testing updates you can then commit these to the repo.
