@_default:
    @just --list

# Install all dependencies
@install:
   @just envfile
   @just pyinstall
   @just precommmitinstall
   @just nltkdownload

# Update all dependencies
@update:
   @just pyupdate
   @just pyinstall
   @just precommitupdate

# Run all checks and tests
@check:
   @just typecheck
   @just templatecheck
   @just test
   @just precommitall

# Start Docker services, run migrations, and start the Django development server
@start:
   @just up
   @just migrate
   @just serve

# Deploy application using Github Actions
@deploy:
    gh workflow run deploy_production.yml

# Install all Python dependencies
[group("uv")]
@pyinstall:
   uv sync --frozen --all-extras --no-install-project

# Update all Python dependencies
[group("uv")]
@pyupdate:
   uv lock --upgrade

# Run the Django management command
[group("django")]
[group("python")]
@dj *ARGS:
   uv run python ./manage.py {{ ARGS }}

# Create a superuser
[group("django")]
@superuser username="admin" email="admin@localhost":
   @just dj createsuperuser \
        --noinput \
        --username="{{ username }}" \
        --email="{{ email }}"

# Run the Django development server
[group("django")]
@serve:
   @just dj tailwind runserver_plus

# Run database migrations
[group("django")]
@migrate:
   @just dj migrate

# Open the Django shell
[group("django")]
@shell:
   @just dj shell_plus

# Clear the cache
[group("django")]
@clearcache:
   @just dj clear_cache

# Validate all templates
[group("django")]
[group("checks")]
@templatecheck:
   @just dj validate_templates

# Set the default site name and domain
[group("django")]
@defaultsite name="RadioFeed" domain="localhost:8000":
    @just dj set_default_site --domain="{{ domain }}" --name="{{ name }}"

# Run unit tests
[group("checks")]
[group("python")]
@test *ARGS:
   uv run pytest {{ ARGS }}

# Type check the code
[group("checks")]
[group("python")]
@typecheck *ARGS:
   uv run pyright {{ ARGS }}

# Start all Docker services
[group("docker")]
@up *ARGS:
   docker compose up -d {{ ARGS }}

# Stop all Docker services
[group("docker")]
@down *ARGS:
   docker compose down {{ ARGS }}

# Run pre-commit manually
[group("precommit")]
@precommit *ARGS:
   uv run --with pre-commit-uv pre-commit {{ ARGS }}

# Install pre-commit hooks
[group("precommit")]
@precommmitinstall:
   @just precommit install
   @just precommit install --hook-type commit-msg

# Update pre-commit hooks
[group("precommit")]
@precommitupdate:
   @just precommit autoupdate

# Re-run pre-commit on all files
[group("precommit")]
@precommitall:
   @just precommit run --all-files

# Download NLTK data
[group("python")]
@nltkdownload:
   uv run xargs -I{} python -c "import nltk; nltk.download('{}')" < ./nltk.txt

# Build local database and add default data
[group("database")]
@dbinit:
   @just migrate
   @just defaultsite
   @just superuser

# Delete local database volume
[group("database")]
[confirm]
@dbremove:
    docker volume rm radiofeed-app_pg_data

# Create a new .env file from .env.example if it doesn't exist
@envfile:
   cp -R -u -p .env.example .env

# Remove all untracked files and directories
[confirm]
@clean:
   git clean -Xdf
