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

You can use these images if you want, or use a local install of PostgreSQL or Redis.

Current tested versions are PostgresSQL 14+ and Redis 6.2+.

### Building development environment

The default settings should just work as-is with the services provided with the `docker-compose.yml` file. If you are using local instances of PostgreSQL, Redis, etc then make a `.env` file and set `DATABASE_URL` and/or `REDIS_URL` accordingly.

To install dependencies for local development:

```bash
poetry install
npm ci
```

This will build your local Docker images and Python and frontend dependencies.

You should then run `docker-compose up -d` to start Docker services if you are using them.

Download NLTK data:

```bash
xargs python -m nltk.downloader <./nltk.txt
```

Next run database migrations and install fixtures:

```bash
python manage.py migrate
python manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
python manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz
```

You can run the `parse_feeds` command detailed below to sync podcasts with their RSS feeds.

Finally, as with any Django project, you should also create a super-user to access the admin section:

```bash
python manage.py createsuperuser
```

### Running development environment

The easiest way to spin up your local development environment is to run [Honcho](https://honcho.readthedocs.io/), which is included as a local dependency:

```bash
honcho start -f honcho.procfile
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

In production it's also a good idea to set `ADMIN_URL` to something other than the default _admin/_. Make sure it ends in a forward slash, e.g. _some-random-path/_.

A Dockerfile is provided for standard container deployments e.g. on Dokku.

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
