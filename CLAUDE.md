# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Radiofeed is a Django-based podcast aggregator (podcatcher) web application. The app uses HTMX for dynamic UI updates, Tailwind CSS for styling, and PostgreSQL for data persistence with full-text search capabilities.

## Development Commands

### Environment Setup

```bash
just install              # Install all dependencies (Python + pre-commit)
just start               # Start Docker services (PostgreSQL, Redis, Mailpit)
just stop                # Stop Docker services
```

### Running the Application

```bash
just serve               # Run development server + Tailwind JIT compiler
just dj [command]        # Run Django management commands (e.g., just dj migrate)
```

### Testing & Quality

```bash
just test [args]         # Run pytest (args optional, e.g., -k test_name)
just tw                  # Run pytest-watcher (auto-run tests on file changes)
just lint                # Run Ruff linter/formatter with --fix
just typecheck [args]    # Run basedpyright type checker
just precommit [args]    # Run pre-commit manually
```

### Running a Single Test

```bash
just test radiofeed/podcasts/tests/test_models.py::TestPodcastQuerySet::test_scheduled
just test -k test_scheduled  # Run all tests matching pattern
```

### Database Commands

```bash
just dj makemigrations   # Create new migrations
just dj migrate          # Apply migrations
just psql radiofeed      # Connect to PostgreSQL via docker compose
```

### Updating Dependencies

```bash
just update              # Update Python dependencies + pre-commit hooks
```

## Architecture

### Django Apps Structure

**radiofeed.podcasts** - Core podcast data management

- Models: `Podcast`, `Category`, `Subscription`, `Recommendation`, `Season`
- Handles RSS feed URLs, metadata, scheduling, and recommendations
- Uses `.scheduled()` queryset for smart feed parser prioritization based on activity
- Tracks feed parse history (etag, last-modified) for efficient HTTP conditional requests

**radiofeed.episodes** - Episode/audio content management

- Models: `Episode`, `Bookmark`, `AudioLog`
- Tracks user listening history with playback position and duration
- Episode bookmarking and navigation (next/previous across feed)

**radiofeed.users** - User accounts and preferences

- Custom User model extending AbstractUser
- Notification preferences and email digest settings

### Feed Parsing Pipeline

Feed parsing is triggered via management commands (expected to run via cron):

1. **Scheduling** (`radiofeed.parsers.scheduler`): Dynamic frequency calculation based on episode publication intervals (1 hour to 3 days)
2. **HTTP Fetching** (`radiofeed.parsers.rss_fetcher`): Conditional requests using ETag/If-Modified-Since headers
3. **RSS Parsing** (`radiofeed.parsers.rss_parser`): XPath-based parsing with Pydantic validation
4. **Episode Sync**: Bulk upsert (batch size: 300) with conflict resolution on (podcast, guid)
5. **Error Handling**: Retry logic with exponential backoff (max 12 retries before deactivation)

Management commands:

```bash
just dj parse_feeds --limit 360    # Parse up to 360 scheduled podcasts
just dj send_notifications          # Email digests of new episodes
just dj create_recommendations      # Build podcast similarity matrix
```

### HTMX Integration Pattern

The app is HTMX-first with custom middleware for enhanced request/response handling:

- **HtmxCacheMiddleware**: Sets Vary headers for proper caching with HTMX
- **HtmxMessagesMiddleware**: Injects Django messages as out-of-band content
- **HtmxRedirectMiddleware**: Converts redirects to HX-Location headers
- **SearchMiddleware**: Parses search queries and attaches to `request.search`
- **PlayerMiddleware**: Tracks currently playing episode in session

Templates use HTMX attributes (`hx-get`, `hx-swap`, `hx-target`) for dynamic updates without full page reloads.

### QuerySet Pattern with Search

Custom queryset managers extend Django's with app-specific methods:

- **Searchable mixin**: Adds `.search(query)` using PostgreSQL full-text search with SearchRank
- **PodcastQuerySet**: `.subscribed(user)`, `.scheduled()`, `.recommended(user)`, `.published()`
- **EpisodeQuerySet**: Navigation helpers, filtering by season/podcast
- **BookmarkQuerySet/AudioLogQuerySet**: User-specific filtering with search

Example:

```python
Podcast.objects.search("python").subscribed(request.user)
```

### Background Processing

Uses thread pools (not Celery) for batch operations:

- **`db_threadsafe` decorator**: Ensures proper database connection cleanup in threads
- **`thread_pool_map()`**: Batch processing with configurable size (default: 500 items/batch)
- Expected execution via cron jobs or scheduler (APScheduler, Celery Beat, etc.)

### Custom Utilities

**Cover Image Processing** (`radiofeed.covers`)

- Fetches and resizes cover images to multiple variants (card, detail, tile)
- WebP compression with PIL/Pillow
- URL signing for security using Django's Signer

**HTML Sanitization** (`radiofeed.sanitizer`)

- Two-stage: HTML → Markdown (via markdownify) → Safe HTML (via markdown-it + nh3)
- XSS protection with whitelist of safe tags
- `strip_html()`: Remove all markup for plain text

**RSS/Atom Parser** (`radiofeed.parsers`)

- XPathParser with namespace support (iTunes, Google Play, Podcast Index, Media RSS)
- Pydantic models for validation: Feed, Item, with custom validators for:
  - Duration parsing (convert to HH:MM:SS, validate ranges)
  - Pub date validation (reject future dates)
  - URL normalization
  - Audio mimetype validation
  - Episode type classification (full, trailer, bonus)

### Database Optimization

- **PostgreSQL 18** with connection pooling via Psycopg 3 (min: 2, max: 100 connections)
- **Full-text search**: GIN indexes on SearchVectorField, no external search engine needed
- **Composite indexes**: Optimize common queries (scheduling, pagination, user-specific filters)
- **Unique constraints**: (podcast, guid) for episodes, (user, podcast) for subscriptions

### Testing Approach

- **Framework**: pytest + pytest-django with factory_boy for test data
- **Coverage requirement**: 100% (`--cov-fail-under=100`)
- **Test organization**: Co-located with apps (`radiofeed/*/tests/`)
- **Global fixtures**: `_settings_overrides` for dummy cache, fast password hasher
- **Patterns**: Factory-based creation, `@pytest.mark.django_db`, integration tests

## Configuration

### Settings Module

- `config.settings`: Main settings file
- Environment variables via environs (`.env` file for local overrides)
- Key settings: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `DEBUG`

### Pre-commit Hooks

Extensive pre-commit configuration includes:

- Ruff (linting + formatting)
- rustywind (Tailwind class ordering)
- djhtml/djlint (Django template formatting/linting)
- pyupgrade + django-upgrade (Python/Django version compatibility)
- gitleaks (secret detection)
- shellcheck, hadolint (shell scripts, Dockerfile)
- commitlint (conventional commits)

Install hooks with: `just precommitinstall`

### Development Environment Variables

Set from `.env` file. Copy from `.env.example` and adjust as needed.

- `DEBUG=true`
- `USE_DEBUG_TOOLBAR=true`
- `USE_BROWSER_RELOAD=true`
- `USE_WATCHFILES=true` (auto-reload on file changes)
- `USE_COLLECTSTATIC=false`
- `USE_CONNECTION_POOL=false` (for tests)

## Common Patterns

### Creating a New Django Model

1. Add model to appropriate app (`podcasts`, `episodes`, `users`)
2. Consider adding custom queryset manager if filtering/search needed
3. Run `just dj makemigrations`
4. Review migration, then `just dj migrate`
5. Add factory in `radiofeed/tests/fixtures.py` (if needed for tests)
6. Create tests in `radiofeed/{app}/tests/test_models.py`

### Adding a New View

1. Create view in `radiofeed/{app}/views.py`
2. Register URL in `config/urls.py` or app-specific `urls.py`
3. Create template in `templates/{app}/`
4. Use HTMX attributes for dynamic updates (`hx-get`, `hx-swap`)
5. Consider response helpers: `render_partial_response()`, `render_paginated_response()`
6. Add tests in `radiofeed/{app}/tests/test_views.py`

### Modifying Feed Parsing

- RSS parsing logic in `radiofeed/parsers/rss_parser.py`
- Pydantic models in `radiofeed/parsers/models.py`
- XPath queries support iTunes, Google Play, Media RSS namespaces
- Add validators to Pydantic models for new fields
- Update `parse_feed()` in `radiofeed/parsers/feed_parser.py` for transaction logic

### TypedHttpRequest Pattern

Use typed request classes for better type checking:

```python
from radiofeed.http.request import AuthenticatedHttpRequest

def my_view(request: AuthenticatedHttpRequest) -> HttpResponse:
    user = request.user  # Guaranteed to be authenticated User, not AnonymousUser
```

## Stack

- **Backend**: Django 6.0, Python 3.14
- **Database**: PostgreSQL 18 with full-text search (GIN indexes)
- **Cache**: Redis 8
- **Frontend**: HTMX, AlpineJS, Tailwind CSS
- **Image Processing**: Pillow, WebP compression
- **HTTP Client**: httpx with streaming support
- **RSS Parsing**: lxml (XPath), Pydantic validation
- **Sanitization**: nh3, markdown-it, markdownify

## Deployment

- Dockerfile provided for container deployments
- K3s Ansible playbooks in `ansible/` directory for multi-server deployment
- Environment variables required: `ALLOWED_HOSTS`, `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `SENTRY_URL`
- Optional Mailgun integration: `EMAIL_HOST`, `MAILGUN_API_KEY`

## Code Style Notes

- Use Ruff for linting/formatting (runs in pre-commit)
- Type hints required (checked by basedpyright)
- Django 5.1+ patterns (enforced by django-upgrade)
- Python 3.14 syntax (enforced by pyupgrade)
- Conventional commits (enforced by commitlint)
