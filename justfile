ansible_dir := invocation_directory() / "ansible"
script_dir := ansible_dir / "scripts"

@_default:
    just --list

# Install all dependencies
[group('development')]
install: pyinstall precommitinstall nltkdownload

# Update all dependencies
[group('development')]
update: pyupdate pyinstall precommitupdate

# Install all Python dependencies
[group('development')]
pyinstall:
   uv sync --frozen --all-extras --no-install-project

# Update all Python dependencies
[group('development')]
pyupdate:
   uv lock --upgrade

# Run Django management command
[group('development')]
dj *args:
   uv run python ./manage.py {{ args }}

# Run Django development server + Tailwind
[group('development')]
serve:
   @just dj tailwind runserver

# Run all tests
[group('development')]
test-all: test e2e

# Run unit tests
[group('development')]
test *args:
   uv run pytest {{ args }}

# Run e2e tests with Playwright (headless)
[group('development')]
e2e *args:
   uv run pytest -c playright.ini {{ args }}

# Run e2e tests with a visible browser window
[group('development')]
e2e-headed *args:
   uv run pytest -c playright.ini --headed {{ args }}

# Install Playwright browsers (run once after uv sync)
[group('development')]
playwright-install:
   uv run playwright install chromium

# Run pytest-watcher
[group('development')]
tw:
   uv run ptw .

# Run type checks
[group('development')]
typecheck *args:
   uv run basedpyright {{ args }}

# Run linting
[group('development')]
lint:
   uv run ruff check --fix

# Download NLTK data
[group('development')]
nltkdownload:
   uv run xargs -I{} python -c "import nltk; nltk.download('{}')" < ./nltk.txt

# Run docker compose
[group('development')]
dc *args:
   docker compose {{ args }}

# Start all Docker services
[group('development')]
start *args:
   @just dc up -d --remove-orphans {{ args }}

# Stop all Docker services
[group('development')]
stop *args:
   @just dc down {{ args }}

# Run Psql
[group('development')]
psql *args:
   @just dc exec postgres psql -U postgres {{ args }}

# Run pre-commit manually
[group('development')]
precommit *args:
   uv run --with pre-commit-uv pre-commit {{ args }}

# Install pre-commit hooks
[group('development')]
precommitinstall:
   @just precommit install
   @just precommit install --hook-type commit-msg

# Update pre-commit hooks
[group('development')]
precommitupdate:
   @just precommit autoupdate

# Re-run pre-commit on all files
[group('development')]
precommitall:
   pre-commit run --all

# Run Ansible playbook
[group('deployment')]
apb playbook *args:
    ansible-playbook -i {{ ansible_dir / "hosts.yml" }} {{ ansible_dir / playbook + ".yml" }} {{ args }}

# Run Github workflow
[group('deployment')]
gh workflow *args:
    gh workflow run {{ workflow }}.yml {{ args }}

# Run Django manage.py commands on production server
[group('production')]
[confirm("WARNING!!! Are you sure you want to run this command on production? (y/N)")]
rdj *args:
    @just remote_script manage.sh dj_manage {{ args }}

# Run Psql commands remotely on production database
[group('production')]
[confirm("WARNING!!! Are you sure you want to run this command on production? (y/N)")]
rpsql *args:
    @just remote_script psql.sh psql {{ args }}

# Run Kubectl commands remotely on production cluster
[group('production')]
kube *args:
    @just remote_script kubectl.sh kubectl {{ args }}

[private]
remote_script script playbook *args:
    #!/usr/bin/bash
    if [ ! -f "{{ script_dir / script }}" ]; then
        echo "{{ script }} not found, generating it..."
        mkdir -p {{ script_dir }}
        just apb {{ playbook }}
    fi
    {{ script_dir / script }} {{ args }}
