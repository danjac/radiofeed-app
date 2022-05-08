This is the source code for a simple, easy to use podcatcher web application. You are free to use this source to host the app yourself.

![desktop](/screenshots/desktop.png?raw=True)

## Running Radiofeed on your local machine

For ease of local deployments a `docker-compose.yml` is provided which includes:

* PostgreSQL
* Redis
* Mailhog

You can run this if you wish, or use a local install of PostgreSQL or Redis:

```bash
    docker-compose build
    docker-compose up -d
```

Copy the file `.env.example` to `.env` and set the variables accordingly.

Create a Python virtualenv and install dependencies (you will need **Python 3.10** to run this application):

```bash
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
```

Install the NLTK corpora:

```bash
    mkdir ./venv/share/nltk
    xargs python -m nltk.downloader -d ./venv/share/nltk_data <./nltk.txt
```

Finally, run migrations and start the Django server:

```bash
    python manage.py migrate
    python manage.py runserver
```

Run tests using `pytest`:

```bash
    python -m pytest
```

You can install default iTunes categories and approx 200 common podcasts from fixtures:

```bash
    python manage.py loaddata podcasts radiofeed/podcasts/fixtures/categories.json.gz
    python manage.py loaddata podcasts radiofeed/podcasts/fixtures/podcasts.json.gz
```

To run frontend builds first install dependencies and run the watch command in another terminal:

```bash
    npm ci
    npm run watch
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
