script_dir := justfile_directory() / "scripts"
kubeconfig := env("KUBECONFIG", env("HOME") / ".kube/radiofeed.yaml")

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
test-all: test test-e2e

# Run unit tests
[group('development')]
test *args:
   uv run pytest {{ args }}

# Run e2e tests with Playwright (headless)
[group('development')]
test-e2e *args:
   uv run pytest -c playright.ini {{ args }}

# Run e2e tests with a visible browser window
[group('development')]
test-e2e-headed *args:
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
   uv run djlint --lint templates/

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

# Fetch kubeconfig from the production server (writes to ~/.kube/radiofeed.yaml)
[group('deployment')]
get-kubeconfig:
    {{ script_dir }}/get-kubeconfig.sh

# Install or upgrade the radiofeed Helm chart
[group('deployment')]
helm-upgrade:
    helm upgrade --install radiofeed helm/radiofeed/ \
        --kubeconfig {{ kubeconfig }} \
        -f helm/radiofeed/values.yaml \
        -f helm/radiofeed/values.secret.yaml

# Install or upgrade the observability Helm chart
[group('deployment')]
helm-upgrade-observability:
    helm dependency update helm/observability/
    helm upgrade --install observability helm/observability/ \
        --kubeconfig {{ kubeconfig }} \
        --namespace monitoring \
        --create-namespace \
        -f helm/observability/values.yaml \
        -f helm/observability/values.secret.yaml

# Run Github workflow
[group('deployment')]
gh workflow *args:
    gh workflow run {{ workflow }}.yml {{ args }}

# Run Django manage.py commands on production server
[group('production')]
[confirm("WARNING!!! Are you sure you want to run this command on production? (y/N)")]
rdj *args:
    {{ script_dir }}/manage.sh {{ args }}

# Run Psql commands remotely on production database
[group('production')]
[confirm("WARNING!!! Are you sure you want to run this command on production? (y/N)")]
rpsql *args:
    {{ script_dir }}/psql.sh {{ args }}

# Run Kubectl commands on the production cluster
[group('production')]
kube *args:
    kubectl --kubeconfig {{ kubeconfig }} {{ args }}

# Deploy a new image to production (pre-upgrade hook runs migrations before rollout)
[group('production')]
[confirm("WARNING!!! Are you sure you want to deploy to production? (y/N)")]
deploy image:
    helm upgrade radiofeed helm/radiofeed/ \
        --kubeconfig {{ kubeconfig }} \
        --atomic \
        --set "image={{ image }}" \
        -f helm/radiofeed/values.yaml \
        -f helm/radiofeed/values.secret.yaml
