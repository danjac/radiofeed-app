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

For the common case:

> make test

## Deployment

> make push

There is also a Github actions workflow set up to automatically run tests and deploy the main branch.

## Maintenance

There is an Ansible playbook configured to clean up Docker containers, run server updates etc:

> ansible-playbook maintenance.yml

## License

This project is covered by MIT license.
