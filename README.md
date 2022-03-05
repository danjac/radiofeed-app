This is the source code for [jCasts](https://jcasts.io), a simple, easy to use podcatcher web application. You are free to use this source to host the app yourself.

![desktop](/screenshots/desktop.png?raw=True)

## Running jcasts on your local machine

Local development requires:

* docker
* docker-compose

Just run the Makefile:

> make

To update podcast data and download episodes from their RSS feeds:

> ./scripts/manage schedule_podcast_feeds

You can then generate podcast recommendations with this command:

> ./scripts/manage make_recommendations

You an also create a super user if you wish to access the Django admin:

> ./scripts/manage createsuperuser

You can access the development app in your browser at _http://localhost:8000_.

To run unit tests:

> ./scripts/runtests [...]

This script takes the same arguments as _./python -m pytest_ e.g.:

> ./scripts/runtests -x --ff

For the common case:

> make test

## Upgrade

To upgrade Python dependencies you should install pip-tools https://github.com/jazzband/pip-tools on your local machine (not the Docker container):

> pip install --user pip-tools

You also need **npm-check-updates**:

> sudo npm install -g npm-check-updates

Then just run `make upgrade`.

To add a new dependency, add it to **requirements.in** and then run `pip-compile`. This will update *requirements.txt* accordingly. You can then rebuild the containers with `make build` and commit the changes to the repo.

## Deployment

> make push

Once deployed you can use the *dokku-manage* script to run Django commands remotely on your Dokku instance.

First set the environment variable *JCASTS_SSH* to point to your IP address or domain:

> export JCASTS_SSH=jcasts.io

You can also set *JCASTS_APPNAME* if different to *jcasts*.

Then just run e.g.

> ./scripts/dokku-manage shell

## Maintenance

There is an Ansible playbook configured to clean up Docker containers, run server updates etc:

> ansible-playbook maintenance.yml

## License

This project is covered by MIT license.
