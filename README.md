This is the source code for a simple, easy to use podcatcher web application. You are free to use this source to host the app yourself.

![desktop](/screenshots/desktop.png?raw=True)

## Running podtracker on your local machine

Local development requires:

* docker
* docker-compose

Just run the Makefile to build and start the containers:

> make up

To update podcast data and download episodes from their RSS feeds:

> ./bin/manage schedule_podcast_feeds

You can then generate podcast recommendations with this command:

> ./bin/manage make_recommendations

You an also create a super user if you wish to access the Django admin:

> ./bin/manage createsuperuser

You can access the development app in your browser at _http://localhost:8000_.

To run unit tests:

> ./bin/pytest [...]

This script takes the same arguments as _./python -m pytest_ e.g.:

> ./bin/pytest -x --ff

For the common case:

> make test

## Upgrade

To upgrade Python dependencies you should install pip-tools https://github.com/jazzband/pip-tools on your local machine (not the Docker container):

> pip install --user pip-tools

Then just run `make upgrade`.

To add a new dependency, add it to **requirements.in** and then run `pip-compile`. This will update *requirements.txt* accordingly. You can then rebuild the containers with `make build` and commit the changes to the repo.

## Deployment

The following environment variables should be set in your production installation:

```
    DJANGO_SETTINGS_MODULE='podtracker.settings.production'
    DATABASE_URL=''
    REDIS_URL=''
    ADMIN_URL='/some-random-url/'
    ADMINS='me@site.com'
    ALLOWED_HOSTS='my-domain'
    MAILGUN_API_KEY='<mailgun_api_key>'
    MAILGUN_SENDER_DOMAIN='my-domain'
    SECRET_KEY='<secret>'
    SENTRY_URL='<sentry-url>'
    HOST_COUNTRY=''
    TWITTER_ACCOUNT='my_twitter_handle'
    CONTACT_EMAIL='me@site.com'
```

The following commands should be set up to run as cron jobs (or equivalent scheduled workers):

`python manage.py schedule_podcast_feeds`

`python manage.py make_recommendations`

`python manage.py send_recommendation_emails`

The _schedule_podcast_feeds_ command has a number of options so you can set up multiple schedules accordingly. For example the _--primary_ flag will sync any feeds subscribed by users, so it might be better to run that more often.
