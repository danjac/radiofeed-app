# Radiofeed

![coverage](/static/img/coverage.svg?raw=True)

A modern, self-hosted podcast aggregator (podcatcher) web application built with Django, HTMX, and Tailwind CSS.

## Features

- **Podcast Discovery**: Browse and search thousands of podcasts with full-text search
- **Smart Feed Updates**: Intelligent RSS feed parsing with conditional requests and dynamic scheduling
- **Episode Playback**: In-browser audio player with playback position tracking
- **Personalized Recommendations**: Algorithm-based podcast suggestions based on your subscriptions
- **Bookmarks & History**: Save favorite episodes and track listening progress
- **Email Notifications**: Optional digests of new episodes from subscribed podcasts
- **Progressive Web App**: Installable as a mobile/desktop app
- **OAuth Support**: Sign in with GitHub or Google

## Technology Stack

- **Backend**: [Django 6.0](https://djangoproject.com) (Python 3.14)
- **Frontend**: [HTMX](https://htmx.org), [AlpineJS](https://alpinejs.dev), [Tailwind CSS](https://tailwindcss.com)
- **Database**: [PostgreSQL 18](https://www.postgresql.org/) with full-text search
- **Cache**: Redis 8
- **RSS Parsing**: lxml (XPath) with Pydantic validation
- **Image Processing**: Pillow with WebP compression

## Quick Start

### Prerequisites

- Python 3.14 (install via `uv python install 3.14.x` if needed)
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer
- [just](https://github.com/casey/just) - Command runner (optional but recommended)
- Docker & Docker Compose (required for development services)

### Installation

1. **Clone the repository**

    ```bash
    git clone https://github.com/yourusername/radiofeed-app.git
    cd radiofeed-app
    ```

2. **Start development services (do this first!)**

    ```bash
    just start
    ```

    This starts Docker containers via `docker-compose.yml` for:

    - **PostgreSQL 18** (port 5432)
    - **Redis 8** (port 6379)
    - **Mailpit** for email testing (UI: <http://localhost:8025>)

    These services must be running before proceeding with the next steps.

3. **Create environment file**

    ```bash
    cp .env.example .env
    ```

    The `.env.example` file contains required development settings (e.g., `DEBUG=true`, `USE_DEBUG_TOOLBAR=true`) that are configured to work with the Docker Compose services.

4. **Install dependencies**

    ```bash
    just install
    ```

    This will:

    - Install Python dependencies with uv
    - Set up pre-commit hooks
    - Download NLTK data for text processing

5. **Run database migrations**

    ```bash
    just dj migrate
    ```

6. **Create a superuser**

    ```bash
    just dj createsuperuser
    ```

7. **Start the development server**

    ```bash
    just serve
    ```

    The app will be available at <http://localhost:8000>

### Environment Configuration

**The `.env.example` file contains default development settings configured to work with the `docker-compose.yml` services.** Simply copy it to `.env` as shown in step 3 above.

If you need to customize settings (e.g., using local PostgreSQL/Redis instead of Docker, or adding OAuth credentials):

1. Edit your `.env` file to customize:
    - `DATABASE_URL` - PostgreSQL connection string (default works with Docker Compose)
    - `REDIS_URL` - Redis connection string (default works with Docker Compose)
    - `SECRET_KEY` - Django secret key (auto-generated in development)
    - `DEBUG` - Enable debug mode (set to `true` for development)
    - `USE_DEBUG_TOOLBAR` - Enable Django Debug Toolbar (set to `true` for development)
    - OAuth credentials for GitHub/Google login (optional)

## Development

### Common Commands

```bash
just                     # List all available commands
just serve              # Run dev server + Tailwind compiler
just test               # Run test suite
just test -k pattern    # Run specific tests
just tw                 # Run tests in watch mode
just lint               # Run code formatters and linters
just typecheck          # Run type checker (basedpyright)
just dj <command>       # Run Django management commands
```

### Testing

The project maintains 100% code coverage:

```bash
just test                      # Run all tests with coverage
just test radiofeed/podcasts   # Test specific module
just tw                        # Watch mode - auto-run on changes
```

### Code Quality

Pre-commit hooks run automatically on commit:

```bash
just precommit run --all-files    # Run manually
just precommitupdate              # Update hook versions
```

Hooks include:

- **Ruff** - Fast Python linting and formatting
- **basedpyright** - Type checking
- **djhtml/djlint** - Django template formatting
- **rustywind** - Tailwind class sorting
- **gitleaks** - Secret detection
- **commitlint** - Conventional commit messages

### Adding Podcasts

The app doesn't include a web UI for adding podcasts yet. Use the Django admin or management commands:

```bash
# Via admin
just dj createsuperuser
# Then visit http://localhost:8000/admin/

# Via shell
just dj shell
>>> from radiofeed.podcasts.models import Podcast
>>> Podcast.objects.create(rss="https://example.com/feed.xml")
```

### Task runner

This project uses [Django tasks](https://docs.djangoproject.com/en/6.0/topics/tasks/) for running background jobs without Celery. The `just dj` command can be used to run these tasks:

```bash
just dj db_worker
```

### Feed Parsing

**NOTE**: ensure task runner is running.

Podcast feeds are parsed via management commands (typically run via cron):

```bash
just dj parse_podcast_feeds --limit 360        # Parse up to 360 scheduled podcasts
just dj send_episode_updates             # Email new episode notifications
just dj create_podcast_recommendations         # Generate podcast recommendations
```

The parser features:

- Conditional HTTP requests (ETag/If-Modified-Since)
- Dynamic scheduling based on episode frequency
- Exponential backoff on errors
- Bulk episode upserts for efficiency
- Support for iTunes, Google Play, and Podcast Index namespaces

## Deployment

For production deployment to Hetzner Cloud with Cloudflare CDN/SSL, see the [Deployment Guide](DEPLOYMENT.md). It should be possible to deploy to any Docker compatible hosting provider with some adjustments to the deployment scripts.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the code style (Ruff will enforce this)
4. Write tests to maintain 100% coverage
5. Commit using conventional commits (`feat:`, `fix:`, `docs:`, etc.)
6. Push to your fork and submit a pull request

Pre-commit hooks will run automatically to ensure code quality.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/radiofeed-app/issues)
- **Security**: See [SECURITY.md](SECURITY.md) for reporting vulnerabilities

## Acknowledgments

- RSS feed parsing inspired by various podcast aggregators
- Uses excellent open-source libraries (Django, HTMX, PostgreSQL)
- Thanks to all contributors!
