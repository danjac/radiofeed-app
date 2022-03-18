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

## Configuration

There are several Ansible playbooks for configuring and maintaining your deployment.

First copy _hosts.example_ to _hosts_ and add the correct IP address.

You should also create a file _.vault_pass_ and include the password for Ansible vault (this file should not be committed to the repo).

Finally copy the file _vars.yml.template_ to _vars.yml_ and enter the correct values. When you're done, make sure to encrypt the file:

> ansible-vault encrypt vars.yml

Again, _vars.yml_ should not be included in your repo. You may wish to store it in a secure location, such as LastPass.

## Deployment

The deployment requires Dokku https://dokku.com/. Follow the instructions to install Dokku on a host machine, or use a preconfigured VM or similar (for example Digital Ocean offers a Droplet preconfigured with Dokku).

Once you have set up your configuration variables as instructed above, you can now update your Dokku instance with these environment variables using the provided Ansible playbook:

> ansible-playbook configure.yml [ask pass](--ask-pass)

First configure local deployment:

> git remote add dokku dokku@jcasts.io:jcasts

(Change _jcasts.io_ to your domain).

You can now deploy to your Dokku install:

> make push

Once deployed you can use the *dokku-manage* script to run Django commands remotely on your Dokku instance.

First set the environment variable *JCASTS_SSH* to point to your IP address or domain:

> export JCASTS_SSH=jcasts.io

You can also set *JCASTS_APPNAME* if different to *jcasts*.

Then just run e.g.

> ./scripts/dokku-manage shell

## Maintenance

There is an Ansible playbook configured to clean up Docker containers, run server updates etc:

> ansible-galaxy collection install geerlingguy.swap

> ansible-playbook maintenance.yml

## License

This project is covered by MIT license.
