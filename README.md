This is a very simple MVP podcast app. It has the following features:

1. Sync podcasts with their RSS feeds
2. Discover podcasts through iTunes categories
3. Search individual podcasts and episodes
4. Play episodes using an embedded HTML5 audio player
5. Favorite episodes
6. Subscribe to individual podcast feeds
7. Recommend similar podcasts

## Running Audiotrails on your local machine

Local development uses Podman and Buildah:

https://podman.io/getting-started/installation

https://buildah.io/

To get started, run _./bootstrap.sh_. This will create a new pod, _audiopod_ and create and run the required containers.

Once this is installed, you can start your local instance again by just running

> podman pod start audiopod

You can check the state of the pod if troubleshooting using

> podman pod inspect audiopod

See the Podman docs for more details.

Next load the categories and sample podcasts into the database:

> ./scripts/manage seed_podcast_data

To update podcast data and download episodes from their RSS feeds:

> ./scripts/manage sync_podcast_feeds --use-celery

You an also create a super user if you wish to access the Django admin:

> ./scripts/manage createsuperuser

You can access the development app in your browser at http://localhost:8000.

To run unit tests:

> ./scripts/runtests [...]

This script takes the same arguments as Django _./manage.py.test_:

> ./scripts/runtests --keepdb --failfast --parallel

**Note** due to migration issues the celerybeat container may not start immediately. If you need to use celerybeat in development, just run:

> podman start audiopod-celerybeat

Issue is covered here: https://github.com/danjac/audiotrails/issues/3

## Deployment

This app has been configured to run on ![Dokku](https://github.com/dokku/dokku). You can set up for example a Dokku Droplet on Digital Ocean available as one of their one-click apps. Set up your DNS with your provider as per the Dokku instructions.

SSH into your Dokku server and create the app and add the domain (assuming "audiotrails" is your app name, and "audiotrails-domain.com" your domain):

> dokku apps:create audiotrails

> dokku domains:add audiotrails audiotrails-domain.com

Make sure you add buildpacks for PostgreSQL and Redis:

> dokku plugin:install https://github.com/dokku/dokku-postgres.git

> dokku postgres:create audiotrails_db

> dokku postgres:link audiotrails_db audiotrails

> dokku plugin:install https://github.com/dokku/dokku-redis.git

> dokku redis:create audiotrails_redis

> dokku redis:link audiotrails_redis audiotrails

These instructions will automatically set up the environment variables **DATABASE_URL** and **REDIS_URL**.

The next step is to configure your environment variables. Copy the file _vars.yml.template_ to _vars.yml_ and enter the relevant values. You should encrypt this file using ansible-vault:

> ansible-vault encrypt vars.yml

Note that _vars.yml_ is ignored by Git, so if you want to keep the file safe outside your development machine you should use a solution like LastPass or Bitwarden.

You can then run an ansible playbook to set these variables:

> ansible-playbook configure.yml

Next add to Git and deploy:

> dokku git:set --global deploy-branch main

> dokku ssh:add deploy-ssh /path/to/my_pub

> git remote add dokku dokku@my-domain-or-ip-address:audiotrails

Once the app is deployed set up LetsEncrypt for SSL protection:

> dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git

> dokku letsencrypt audiotrails

> dokku letsencrypt:cron-job --add

Next set up celery and celerybeat workers:

> dokku ps:scale audiotrails worker=1

> dokku ps:scale audiotrails beat=1

You should now be able to access the Django management commands:

> dokku run python manage.py [command][...options]

Use the Django shell or relevant commands to set up an admin user, and set the default Site to point to your domain. You can then run _loaddata_ and _sync_podcast_feeds_ commands to add the categories and podcasts and sync the RSS feeds.

To deploy just run:

> git push dokku main

## LICENSE

This project is covered by MIT license.
