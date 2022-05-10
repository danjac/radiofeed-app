This is the source code for a simple, easy to use podcatcher web application. You are free to use this source to host the app yourself.

![desktop](/screenshots/desktop.png?raw=True)

## Running Radiofeed on your local machine

Radiofeed requires the following:

* Python 3.10+
* Node 16+

### Additional requirements

For ease of local development a `docker-compose.yml` is provided which includes:

* PostgreSQL
* Redis
* Mailhog

Just run `docker-compose`:

```bash
docker-compose build && docker-compose up -d
```

You can use these images if you want, or use a local install of PostgreSQL or Redis.

### Django setup

Copy the file `.env.example` to `.env` and set the variables accordingly.

Create a Python virtualenv and install dependencies:

```bash
python -m venv venv && \
    source venv/bin/activate && \
    pip install -r requirements.txt -r local-requirements.txt
```

We'll assume all Python commands from this point are run in the virtualenv.

Install the NLTK corpora:

```bash
xargs python -m nltk.downloader <./nltk.txt
```

Finally, run migrations and start the Django server:

```bash
python manage.py migrate
```

You can also install default iTunes categories and approx 200 sample podcasts from fixtures:

```bash
python manage.py loaddata podcasts \
    radiofeed/podcasts/fixtures/categories.json.gz \
    radiofeed/podcasts/fixtures/podcasts.json.gz
```

This should provide some useful data to get started with.

### Frontend setup

To install frontend dependencies just run `npm ci`.

### Running development environment

The easiest way to run your local development environment is using [Honcho](https://honcho.readthedocs.io/):

```bash
honcho -f Procfile.local start
```

This will start up:

* Django development server
* [Huey](https://huey.readthedocs.io/) for running scheduled tasks and queues
* `tailwindcss` and `esbuild` for building frontend assets on the fly

Honcho should be installed in your virtualenv.

Tests can be run with `pytest`:

```bash
python -m pytest
```

## Deployment

The following environment variables should be set in your production installation:

```
DJANGO_SETTINGS_MODULE='radiofeed.settings.production'
DATABASE_URL=''
REDIS_URL=''
ADMIN_URL='some-random-url/'
ADMINS='me@site.com'
ALLOWED_HOSTS='my-domain'
MAILGUN_API_KEY='<mailgun_api_key>'
MAILGUN_SENDER_DOMAIN='my-domain'
SECRET_KEY='<secret>'
SENTRY_URL='<sentry-url>'
CONTACT_EMAIL='my-site@host.com'
```

A `Procfile` is provided for Heroku-like deployments (including Dokku, Railway etc).
