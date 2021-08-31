This is the source code for [jCasts](https://jcasts.io), a simple, easy to use podcatcher web application. You are free to use this source to host the app yourself.

![desktop](/screenshots/desktop.png?raw=True)

## Running jcasts on your local machine

Local development requires docker and docker-compose. Just run the Makefile:

> make

To update podcast data and download episodes from their RSS feeds:

> ./bin/manage parse_podcast_feeds --force-update

You can then generate podcast recommendations with this command:

> ./bin/manage make_recommendations

You an also create a super user if you wish to access the Django admin:

> ./bin/manage createsuperuser

You can access the development app in your browser at http://localhost.

To run unit tests:

> ./bin/runtests [...]

This script takes the same arguments as _./python -m pytest_ e.g.:

> ./bin/runtests -x --ff

## Deployment

This app has been configured to run on [Dokku](https://github.com/dokku/dokku). You can set up for example a Dokku Droplet on Digital Ocean available as one of their one-click apps. Set up your DNS with your provider as per the Dokku instructions.

SSH into your Dokku server and create the app and add the domain (assuming "jcasts" is your app name, and "jcasts-domain.com" your domain):

> dokku apps:create jcasts

> dokku domains:add jcasts jcasts-domain.com

Make sure you add buildpacks for PostgreSQL and Redis:

> dokku plugin:install https://github.com/dokku/dokku-postgres.git

> dokku postgres:create jcasts_db

> dokku postgres:link jcasts_db jcasts

> dokku plugin:install https://github.com/dokku/dokku-redis.git

> dokku redis:create jcasts_redis

> dokku redis:link jcasts_redis jcasts

These instructions will automatically set up the environment variables **DATABASE_URL** and **REDIS_URL**.

The next step is to configure your environment variables. Copy the file _vars.yml.template_ to _vars.yml_ and enter the relevant values. You should encrypt this file using ansible-vault:

> ansible-vault encrypt vars.yml

Note that _vars.yml_ is ignored by Git, so if you want to keep the file safe outside your development machine you should use a solution like LastPass or Bitwarden.

You can then run an ansible playbook to set these variables:

> ansible-playbook configure.yml

Next add to Git and deploy:

> dokku git:set --global deploy-branch main

> dokku ssh:add deploy-ssh /path/to/my_pub

> git remote add dokku dokku@my-domain-or-ip-address:jcasts

Once the app is deployed set up LetsEncrypt for SSL protection:

> dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git

> dokku letsencrypt jcasts

> dokku letsencrypt:cron-job --add

You should now be able to access the Django management commands:

> dokku run jcasts python manage.py [command][...options]

Or remotely:

> ssh dokku@my-domain -t run jcasts ./manage.py [command][...options]

For example, to open the interactive Django shell from your local machine:

> ssh dokku@my-domain -t run jcasts ./manage.py shell_plus

Use the Django shell or relevant commands to set up an admin user, and set the default Site to point to your domain. You can then run the *seed_podcast_data* and *parse_podcast_feeds* Django commands to add the categories and podcasts and sync the RSS feeds.

To deploy just run:

> git push dokku main

There is also a Github actions workflow set up to automatically run tests and deploy the main branch.

## Maintenance

There is an Ansible playbook configured to clean up Docker containers, run server updates etc:

> ansible-playbook maintenance.yml

## License

This project is covered by MIT license.
