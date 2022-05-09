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
    pip install -r requirements.txt
```

We'll assume all Python commands from this point are run in the virtualenv.

Install the NLTK corpora:

```bash
mkdir ./venv/nltk_data && \
    xargs python -m nltk.downloader -d ./venv/nltk_data <./nltk.txt
```

Finally, run migrations and start the Django server:

```bash
python manage.py migrate && python manage.py runserver
```

Run tests using `pytest`:

```bash
python -m pytest
```

You can install default iTunes categories and approx 200 sample podcasts from fixtures:

```bash
python manage.py loaddata podcasts \
    radiofeed/podcasts/fixtures/categories.json.gz \
    radiofeed/podcasts/fixtures/podcasts.json.gz
```

If you want to run scheduled jobs locally (using [Huey](https://huey.readthedocs.io/en/latest/)) run this in another terminal in your virtualenv:

```bash
python manage.py run_huey -w 2
```

### Frontend setup

To run frontend builds first install dependencies and run the watch command in another terminal:

```bash
npm ci && npm run watch
```

This will run `esbuild` and `tailwindcss` to watch for changes in your templates and assets.

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
