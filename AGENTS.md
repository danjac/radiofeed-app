# AGENTS.md

Radiofeed is a Django podcast aggregator using HTMX, AlpineJS, and Tailwind CSS.

## Stack

- **Python 3.14**, **Django 6.0**, **PostgreSQL 18**, **Redis 8**
- **Frontend**: HTMX + AlpineJS + Tailwind CSS (no JS build step; Tailwind compiled via `django-tailwind-cli`)
- **Package manager**: `uv` (not pip/poetry)
- **Task runner**: `just` (see `justfile` for all commands)
- **RSS parsing**: lxml (XPath) with Pydantic validation
- **Background tasks**: Django Tasks (`django-tasks-db`), not Celery

## Project Layout

```
config/             # Django settings, URLs, ASGI/WSGI
radiofeed/          # Main application package
  episodes/         # Episode models, views, feed parsing
  podcasts/         # Podcast models, views, recommendations
  users/            # User models, authentication
  db/               # Database utilities
  http/             # HTTP utilities
  tests/            # Shared test fixtures
templates/          # Django templates (HTMX partials + full pages)
static/             # Static assets
conftest.py         # Root pytest config (fixture plugins)
```

## Commands

All commands use `just`. Run `just` with no arguments to list available commands.

### Linting

```bash
just lint
```

Runs `ruff check --fix` (Python) and `djlint --lint templates/` (Django templates).

Ruff is configured in `pyproject.toml` with extensive rule sets. Target version is `py314`.

### Type Checking

```bash
just typecheck
```

Runs `basedpyright`. Configuration is in `pyproject.toml` under `[tool.pyright]`:

- Mode: `basic`
- Includes: `radiofeed/`
- Excludes: migrations, tests

### Testing

```bash
just test                      # Run all unit tests with coverage
just test radiofeed/podcasts   # Test a specific module
just tw                        # Watch mode (auto-rerun on .py/.html changes)
just e2e                       # End-to-end tests (Playwright, headless)
just e2e-headed                # E2E tests with visible browser
```

- Framework: `pytest` with `pytest-django`
- Settings: `config.settings` (via `DJANGO_SETTINGS_MODULE`)
- Coverage: **100% required** (`--cov-fail-under=100`)
- Test location: colocated in `radiofeed/**/tests/` directories
- Fixtures: registered as plugins in `conftest.py` at project root
- E2E config: `playright.ini` (separate pytest config for Playwright tests, marker `e2e`)
- Parallelism: `pytest-xdist` available, `pytest-randomly` randomizes order
- Database: `--reuse-db` enabled by default

### Pre-commit Hooks

```bash
just precommit run --all-files    # Run all hooks manually
just precommitupdate              # Update hook versions
```

Hooks (see `.pre-commit-config.yaml`): ruff (check + format), absolufy-imports, djhtml/djcss/djjs, djade, djlint, rustywind (Tailwind class sorting), pyupgrade, django-upgrade, shellcheck, hadolint (Dockerfile), gitleaks, commitlint, ansible-lint, terraform fmt/validate, uv-secure, validate-pyproject.

### Django Management

```bash
just dj <command>              # Run any manage.py command
just dj migrate                # Run migrations
just dj shell                  # Django shell
just serve                     # Dev server + Tailwind watcher
```

### Dependencies

This project uses `uv` for Python dependency management, not pip or poetry.

```bash
just install                   # Install all deps (Python, pre-commit, NLTK)
just update                    # Update all deps (uv lock --upgrade + sync + pre-commit)
just pyinstall                 # Install Python deps only (uv sync --frozen)
just pyupdate                  # Update Python deps only (uv lock --upgrade)
```

When adding or removing dependencies, use `uv add <package>` (or `uv add --dev <package>` for dev dependencies). Do not edit `pyproject.toml` or `uv.lock` directly.

JS and other frontend dependencies (other than Tailwind) are downloaded manually (or using curl/wget) and stored under `static/vendor/`. Where possible, use the minified latest stable version. Do not use CDNs or npm/yarn for frontend dependencies.

### Docker Services

```bash
just start                     # Start PostgreSQL, Redis, Mailpit
just stop                      # Stop services
just psql                      # Connect to PostgreSQL
```

## Git Workflow

### Commit Messages

Conventional commits enforced by commitlint. Format: `type: subject`

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

Rules:

- Subject must be lowercase, non-empty, no trailing period
- Header max 100 characters, body lines max 100 characters

### Branching

Create a well-named branch for each change (e.g. `feature-<name>`, `hotfix-<name>`).

Before merging a branch into `main`, squash all commits in the branch into a single commit using `git rebase -i` with fixup. Ensure all tests pass (`just test`) and pre-commit linting passes before merging. When merging into `main`, use `git rebase`, not `git merge`. After merging, run all tests again to verify. **You must have 100% coverage as indicated in by coverage tool before merging a branch.** Delete the branch after merging.

Do NOT push any changes to remote. The user will do so themselves manually when they are satisfied with all changes.

## Code Style

### Python

- Ruff handles linting and formatting (replaces black, isort, flake8, pylint)
- Absolute imports only (`absolufy-imports` enforced)
- isort profile: `black`, first-party: `radiofeed`
- `pyupgrade --py314` applied automatically
- `django-upgrade --target-version 6.0` applied automatically

### Templates

- `djhtml` for HTML/CSS/JS indentation
- `djlint` for Django template linting (profile: `django`)
- `djade` for Django template formatting
- `rustywind` for Tailwind CSS class ordering
- Custom blocks registered with djlint: `cache`, `partialdef`

## Testing Conventions

- Tests use `factory-boy` and `faker` for test data
- Fixtures are organized as pytest plugins in `*/tests/fixtures.py`
- `pytest-mock` for mocking
- `pytest-icdiff` for readable diffs
- Coverage source: `radiofeed/`, omits migrations and test files
- E2E tests are marked with `@pytest.mark.e2e` and excluded from default test runs

## Deployment

Production deploys to a Hetzner Cloud K3s cluster with Cloudflare CDN/SSL. The deployment pipeline is: Terraform (infrastructure) → Cloudflare (DNS/CDN) → Ansible (application).

**No production deployment tasks (Terraform apply/destroy, Ansible playbooks, `rdj`, `rpsql`, `kube`) should be executed without express permission of the user.**

### Terraform

Two Terraform configurations provision infrastructure:

- `terraform/hetzner/` — Hetzner Cloud servers, network, firewall, PostgreSQL volume
- `terraform/cloudflare/` — DNS records, CDN caching, SSL/TLS, security headers

Each has its own `terraform.tfvars.example`. Copy to `terraform.tfvars` and fill in secrets. Never commit `terraform.tfvars`.

```bash
cd terraform/hetzner
terraform init && terraform plan && terraform apply

cd ../cloudflare
terraform init && terraform plan && terraform apply
```

Pre-commit hooks run `terraform fmt` and `terraform validate` automatically.

### Ansible

Ansible playbooks in `ansible/` deploy K3s, PostgreSQL, Redis, the Django app, Traefik ingress, and cron jobs.

```bash
just apb site                  # Full deployment
just apb deploy                # Redeploy application only
just apb upgrade               # Update server packages
```

Key files:

- `ansible/hosts.yml` — Inventory (generated from `terraform output -raw ansible_inventory`, then encrypted with `ansible-vault`)
- `ansible/certs/` — Cloudflare origin certificates (`cloudflare.pem`, `cloudflare.key`)
- `ansible/ssh-keys/` — SSH public keys for server access (`.pub` extension)

### Production Commands

```bash
just kube get pods             # Check pod status
just rdj migrate               # Run migrations on production
just rdj createsuperuser       # Create admin user on production
just rpsql                     # Connect to production database
```

`rdj` and `rpsql` prompt for confirmation before executing.
