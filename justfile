
@_default:
    @just --list

# Install all dependencies
@install: pyinstall precommitinstall nltkdownload

# Update all dependencies
@update: pyupdate pyinstall precommitupdate

# Install all Python dependencies
[group('python')]
@pyinstall:
   uv sync --frozen --all-extras --no-install-project

# Update all Python dependencies
[group('python')]
@pyupdate:
   uv lock --upgrade

## Run the Django management command
[group('python')]
@dj *ARGS:
   uv run python ./manage.py {{ ARGS }}

# Run the Django development server
[group('python')]
@serve:
   @just dj tailwind runserver

# Run unit tests
[group('python')]
@test *ARGS:
   uv run pytest {{ ARGS }}

# Download NLTK data
[group('python')]
@nltkdownload:
   uv run xargs -I{} python -c "import nltk; nltk.download('{}')" < ./nltk.txt

# Run docker compose
[group('docker')]
@dc *ARGS:
   docker compose {{ ARGS }}

# Start all Docker services
[group('docker')]
@dcup *ARGS:
   @just dc up -d {{ ARGS }}

# Stop all Docker services
[group('docker')]
@dcdn *ARGS:
   @just dc down {{ ARGS }}

# Run Psql
[group('docker')]
@psql *ARGS:
   @just dc exec postgres psql -U postgres {{ ARGS }}

# Run pre-commit manually
[group('precommit')]
@precommit *ARGS:
   uv run --with pre-commit-uv pre-commit {{ ARGS }}

# Install pre-commit hooks
[group('precommit')]
@precommitinstall:
   @just precommit install
   @just precommit install --hook-type commit-msg

# Update pre-commit hooks
[group('precommit')]
@precommitupdate:
   @just precommit autoupdate

# Re-run pre-commit on all files
[group('precommit')]
@precommitall:
   @just precommit run --all-files

# Deploy the application to production
[group('github')]
[confirm]
@deploy:
    gh workflow run deploy.yml

# Watch the latest Github Actions workflow
[group('github')]
@watch:
    gh run watch $(gh run list --workflow=deploy.yml --limit 1 --json databaseId --jq '.[0].databaseId')

# ANSIBLE COMMANDS

ansible_dir := "./ansible"

# Run Ansible playbook
[group('ansible')]
@pb playbook *ARGS:
    ansible-playbook -v -i {{ ansible_dir }}/hosts.yml {{ ansible_dir }}/playbooks/{{ playbook }}.yml {{ ARGS }}

# Run Django manage.py commands remotely
[group('ansible')]
rdj *ARGS:
    #!/usr/bin/bash
    if [ ! -f "{{ ansible_dir }}/manage.sh" ]; then
        echo "manage.sh not found, generating it..."
        just pb dj_manage
    fi
    {{ ansible_dir }}/manage.sh {{ ARGS }}

# Run Psql commands remotely
[group('ansible')]
rpsql *ARGS:
    #!/usr/bin/bash
    if [ ! -f "{{ ansible_dir }}/psql.sh" ]; then
        echo "pql.sh not found, generating it..."
        just pb psql
    fi
    {{ ansible_dir }}/psql.sh {{ ARGS }}

# Run Kubectl commands remotely
[group('ansible')]
kubectl *ARGS:
    #!/usr/bin/bash
    if [ ! -f "{{ ansible_dir }}/kubectl.sh" ]; then
        echo "kubectl.sh not found, generating it..."
        just pb kubectl
    fi
    {{ ansible_dir }}/kubectl.sh {{ ARGS }}
