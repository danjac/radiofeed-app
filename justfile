import 'ansible/justfile'

@_default:
    @just --list

# Install all dependencies
@install: envfile pyinstall precommitinstall nltkdownload

# Update all dependencies
@update: pyupdate pyinstall precommitupdate

# Install all Python dependencies
@pyinstall:
   uv sync --frozen --all-extras --no-install-project

# Update all Python dependencies
@pyupdate:
   uv lock --upgrade

# Run the Django management command
@dj *ARGS:
   uv run python ./manage.py {{ ARGS }}

# Run Psql
@psql *ARGS:
   docker compose exec postgres psql -U postgres {{ ARGS }}

# Run the Django development server
@serve:
   @just dj tailwind runserver

# Run unit tests
@test *ARGS:
   uv run pytest {{ ARGS }}

# Start all Docker services
@dcup *ARGS:
   docker compose up -d {{ ARGS }}

# Stop all Docker services
@dcdn *ARGS:
   docker compose down {{ ARGS }}

# Run pre-commit manually
@precommit *ARGS:
   uv run --with pre-commit-uv pre-commit {{ ARGS }}

# Install pre-commit hooks
@precommitinstall:
   @just precommit install
   @just precommit install --hook-type commit-msg

# Update pre-commit hooks
@precommitupdate:
   @just precommit autoupdate

# Re-run pre-commit on all files
@precommitall:
   @just precommit run --all-files

# Download NLTK data
@nltkdownload:
   uv run xargs -I{} python -c "import nltk; nltk.download('{}')" < ./nltk.txt

# Create a new .env file from .env.example if it doesn't exist
@envfile:
   cp -R -u -p .env.example .env

# Deploy the application to production
[confirm]
@deploy:
    gh workflow run deploy.yml

# Watch the latest Github Actions workflow
@watch:
    gh run watch $(gh run list --workflow=deploy.yml --limit 1 --json databaseId --jq '.[0].databaseId')
