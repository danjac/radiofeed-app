
ansible_dir := "./ansible"

@_default:
    @just --list

# Install all dependencies
[group('development')]
@install: pyinstall precommitinstall nltkdownload

# Update all dependencies
[group('development')]
@update: pyupdate pyinstall precommitupdate

# Install all Python dependencies
[group('development')]
@pyinstall:
   uv sync --frozen --all-extras --no-install-project

# Update all Python dependencies
[group('development')]
@pyupdate:
   uv lock --upgrade

## Run the Django management command
[group('development')]
@dj *ARGS:
   uv run python ./manage.py {{ ARGS }}

# Run the Django development server
[group('development')]
@serve:
   @just dj tailwind runserver

# Run unit tests
[group('development')]
@test *ARGS:
   uv run pytest {{ ARGS }}

# Download NLTK data
[group('development')]
@nltkdownload:
   uv run xargs -I{} python -c "import nltk; nltk.download('{}')" < ./nltk.txt

# Run docker compose
[group('development')]
@dc *ARGS:
   docker compose {{ ARGS }}

# Start all Docker services
[group('development')]
@dcup *ARGS:
   @just dc up -d {{ ARGS }}

# Stop all Docker services
[group('development')]
@dcdn *ARGS:
   @just dc down {{ ARGS }}

# Run Psql
[group('development')]
@psql *ARGS:
   @just dc exec postgres psql -U postgres {{ ARGS }}

# Run pre-commit manually
[group('development')]
@precommit *ARGS:
   uv run --with pre-commit-uv pre-commit {{ ARGS }}

# Install pre-commit hooks
[group('development')]
@precommitinstall:
   @just precommit install
   @just precommit install --hook-type commit-msg

# Update pre-commit hooks
[group('development')]
@precommitupdate:
   @just precommit autoupdate

# Re-run pre-commit on all files
[group('development')]
@precommitall:
   @just precommit run --all-files

# Run Ansible playbook
[group('deployment')]
@pb playbook *ARGS:
    ansible-playbook -v -i {{ ansible_dir }}/hosts.yml {{ ansible_dir }}/playbooks/{{ playbook }}.yml {{ ARGS }}

# Deploy the application to production
[group('deployment')]
[confirm]
@deploy:
    gh workflow run deploy.yml

# Watch the latest Github Actions workflow
[group('deployment')]
@watch:
    gh run watch $(gh run list --workflow=deploy.yml --limit 1 --json databaseId --jq '.[0].databaseId')

# Run Django manage.py commands on production server
[group('production')]
rdj *ARGS:
    #!/usr/bin/bash
    if [ ! -f "{{ ansible_dir }}/scripts/manage.sh" ]; then
        echo "manage.sh not found, generating it..."
        just pb dj_manage
    fi
    {{ ansible_dir }}/scripts/manage.sh {{ ARGS }}

# Run Psql commands remotely on production database
[group('production')]
rpsql *ARGS:
    #!/usr/bin/bash
    if [ ! -f "{{ ansible_dir }}/scripts/psql.sh" ]; then
        echo "pql.sh not found, generating it..."
        just pb psql
    fi
    {{ ansible_dir }}/scripts/psql.sh {{ ARGS }}

# Run Kubectl commands remotely on production cluster
[group('production')]
kubectl *ARGS:
    #!/usr/bin/bash
    if [ ! -f "{{ ansible_dir }}/scripts/kubectl.sh" ]; then
        echo "kubectl.sh not found, generating it..."
        just pb kubectl
    fi
    {{ ansible_dir }}/scripts/kubectl.sh {{ ARGS }}
