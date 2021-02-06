
![](/screenshots/podcasts.png)


This is a very simple MVP podcast app. It has the following features:

1. Sync podcasts with their RSS feeds
2. Discover podcasts through iTunes categories
3. Search individual podcasts and episodes
4. Play episodes using an embedded HTML5 audio player
5. Favorite episodes
6. Subscribe to individual podcast feeds
7. Recommend similar podcasts

For local development, first copy the .env.example file:

> cp .env.example .env

To get started, first run migrate and load the categories:

> ./scripts/manage migrate

> ./scripts/manage loaddata radiofeed/podcasts/fixtures/categories.json

You can then import a sample list of podcasts:

> ./scripts/manage loaddata radiofeed/podcasts/fixtures/podcasts.json

Alternatively, use the Django admin to add podcasts.

To sync podcasts and download episodes to the database:

> ./scripts/manage sync_podcast_feeds

## Deployment

This app has been configured to run on ![Dokku](https://github.com/dokku/dokku). You can set up for example a Dokku Droplet on Digital Ocean available as one of their one-click apps. You should also set up an S3 bucket with folders "static" and "media", and create a Cloudfront CDN distribution pointing to this bucket. Set up your DNS with your provider as per the Dokku instructions.

SSH into your Dokku server and create the app and add the domain (assuming "myapp" is your app name, and "myapp.com" your domain):

> dokku apps:create myapp

> dokku domains:add myapp myapp.com

Make sure you add buildpacks for PostgreSQL and Redis:

> dokku plugin:install https://github.com/dokku/dokku-postgres.git

> dokku postgres:create myapp_db

> dokku postgres:link myapp_db myapp

> dokku plugin:install https://github.com/dokku/dokku-redis.git

> dokku redis:create myapp_redis

> dokku redis:link myapp_redis myapp

These instructions will automatically set up the environment variables **DATABASE_URL** and **REDIS_URL**.

Ensure the following environment variables are set (*dokku config:set --no-restart*):

- **ADMINS**: comma separated in form _my full name <name@mysite.com>,other name <othername@mysite.com>_
- **ADMIN_URL**: should be something other than "admin/". Must end in forward slash.
- **ALLOWED_HOSTS**: enter your domains, separated by comma e.g. *mysite.com, myothersite.com*. If you are using wildcard domain with subdomains for each community you just need the wildcard domain without the "*".
- **AWS_ACCESS_KEY_ID**: see your S3 settings
- **AWS_S3_CUSTOM_DOMAIN**: your cloudfront domain e.g. *xyz123abcdefg.cloudfront.net*
- **AWS_STORAGE_BUCKET_NAME**: see your S3 settings
- **BUILDPACK_URL**: should be *https://github.com/heroku/heroku-buildpack-python*
- **DISABLE_COLLECTSTATIC**: set to "1"
- **DJANGO_SETTINGS_MODULE**: should always be *radiofeed.config.settings.production*
- **MAILGUN_API_KEY**: see your Mailgun settings
- **MAILGUN_SENDER_DOMAIN**: see your Mailgun settings
- **SENTRY_URL**: see your Sentry settings
- **SECRET_KEY**: Django secret key. Use e.g. https://miniwebtool.com/django-secret-key-generator/ to create new key.

Next add to Git and deploy:

> dokku git:set --global deploy-branch main

> git remote add dokku dokku@my-domain-or-ip-address:myapp

> ./scripts/deploy

Once the app is deployed set up LetsEncrypt for SSL protection:

> dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git

> dokku config:set --no-restart --global DOKKU_LETSENCRYPT_EMAIL=myname@myemail.com

> dokku letsencrypt myapp

> dokku letsencrypt:cron-job --add

Next set up celery and celerybeat workers:

> dokku ps:scale myapp worker=1

> dokku ps:scale myapp beat=1

You should now be able to access the Django management commands:

> dokku run python manage.py [command] [...options]

Use the Django shell or relevant commands to set up an admin user, and set the default Site to point to your domain. You can then run *loaddata* and *sync_podcast_feeds* commands to add the categories and podcasts and sync the RSS feeds.

## LICENSE

This project is covered by GNU Affero General Public License (AGPL).
