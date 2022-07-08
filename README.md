This is the source code for a simple, easy to use podcatcher web application. You are free to use this source to host the app yourself.

![desktop](/screenshots/desktop.png?raw=True)

## Running Radiofeed on your local machine

Radiofeed requires the following:

* Python 3.10+
* Node 16+
* [Poetry](https://python-poetry.org)

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

Current tested versions are PostgresSQL 14+ and Redis 6.2+.

### Django setup

Copy the file `.env.example` to `.env` and set the variables accordingly. These settings should work as-is with the Docker containers defined in `docker-compose.yml`.

To install dependencies:

```bash
poetry install
```

We'll assume all Python commands from this point are run in your Poetry environment.

Install the NLTK corpora:

```bash
xargs python -m nltk.downloader <./nltk.txt
```

Finally, run migrations:

```bash
python manage.py migrate
```

You can also install default iTunes categories and approx 1000+ sample podcasts from fixtures:

```bash
python manage.py loaddata podcasts \
    radiofeed/podcasts/fixtures/categories.json.gz \
    radiofeed/podcasts/fixtures/podcasts.json.gz
```

This should provide some useful data to get started with.


### Frontend setup

To install frontend dependencies just run `npm ci`.

### Running development environment

The easiest way to spin up your local development environment is using [Honcho](https://honcho.readthedocs.io/):

```bash
honcho -f Procfile.local start
```


This will start up:

* Django development server
* Background workers
* `tailwindcss` and `webpack` for building frontend assets on the fly

Honcho should be installed in your virtualenv.

Tests can be run with `pytest`:

```bash
python -m pytest
```

## Deployment

The following environment variables should be set in your production installation. Some providers may set some of these automatically e.g. `DATABASE_URL`:

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

### Crons

In production you should set up the following cron jobs to run these Django commands (with suggested schedules and arguments):

Parse podcast RSS feeds:

```bash
*/6 * * * * python manage.py feed_updates
```

Generate similar recommendations for each podcast:

```bash
15 6 * * * python manage.py recommendations
```

Send podcast recommendations to users:

```bash
15 9 * * 1 python manage.py recommendations --email
```

An `app.json` configuration with these cron schedules is included for Dokku deployment.

### Updating dependencies

To upgrade Python dependencies just use Poetry:

```bash
poetry update
```

This will update `poetry.lock` which should be commmitted to the repo. Refer to Poetry docs for more details.

If you are using Heroku, Dokku or similar for deployment you should also re-generate the `requirements.txt` file, as Heroku will automatically detect and reinstall any changes:

```bash
poetry export --without-hashes -o requirements.txt
```

You can update frontend dependencies as usual with `npm`:

```bash
npm update
```

Again, the updated `package-lock.json` file should be committed to the repo.
