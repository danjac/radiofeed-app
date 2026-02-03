# RadioFeed

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
   - **Mailpit** for email testing (UI: http://localhost:8025)

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

   The app will be available at http://localhost:8000

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

### Project Structure

```
radiofeed-app/
├── radiofeed/          # Main Django project
│   ├── episodes/       # Episode models, views, audio playback
│   ├── podcasts/       # Podcast models, feed parsing, recommendations
│   ├── users/          # User accounts and preferences
│   └── parsers/        # RSS/Atom feed parsing pipeline
├── config/             # Django settings and URL configuration
├── templates/          # Django templates (HTMX-enhanced)
├── static/             # Static assets (CSS, JS, images)
├── ansible/            # Deployment playbooks for K3s
└── justfile            # Development command shortcuts
```

For detailed architecture documentation, see [CLAUDE.md](CLAUDE.md).

### Testing

The project maintains 100% code coverage:

```bash
just test                      # Run all tests with coverage
just test radiofeed/podcasts   # Test specific module
just tw                        # Watch mode - auto-run on changes
```

Tests use pytest with:
- `factory_boy` for test data generation
- `pytest-django` for Django integration
- `pytest-mock` for mocking
- `pytest-xdist` for parallel execution

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

### Feed Parsing

Podcast feeds are parsed via management commands (typically run via cron):

```bash
just dj parse_feeds --limit 360        # Parse up to 360 scheduled podcasts
just dj send_notifications             # Email new episode notifications
just dj create_recommendations         # Generate podcast recommendations
```

The parser features:
- Conditional HTTP requests (ETag/If-Modified-Since)
- Dynamic scheduling based on episode frequency
- Exponential backoff on errors
- Bulk episode upserts for efficiency
- Support for iTunes, Google Play, and Podcast Index namespaces

## Architecture Highlights

### HTMX-First Design

The frontend uses HTMX for dynamic updates without JavaScript frameworks. Custom middleware handles:
- Out-of-band message injection
- Redirect conversion to HX-Location headers
- Cache control for HTMX requests
- Session-based audio player state

### PostgreSQL Full-Text Search

Uses PostgreSQL's native full-text search instead of external search engines:
- SearchVector fields with GIN indexes
- SearchRank for relevance scoring
- Supports podcast and episode search across multiple fields

### Thread-Pool Background Processing

Instead of Celery, uses Python's ThreadPoolExecutor:
- Simpler deployment (no separate workers)
- Database-safe threading with connection cleanup
- Batch processing (500 items/batch)
- Suitable for ~360 podcasts/run

### Smart Feed Scheduling

Dynamic update frequency based on podcast activity:
- Analyzes episode publication intervals
- Ranges from 1 hour (active) to 3 days (inactive)
- Prioritizes by: new podcasts, subscriber count, promoted status
- Incremental backoff if no new episodes

See [CLAUDE.md](CLAUDE.md) for complete architecture documentation.

## Deployment

RadioFeed can be deployed in several ways, from simple Docker containers to production-ready K3s clusters on Hetzner Cloud.

### Hetzner Cloud + Terraform (Recommended for Production)

For production deployments, we provide Terraform configuration to provision infrastructure on Hetzner Cloud:

**Infrastructure:**
- K3s control plane + load balancer (Traefik)
- Dedicated database server (PostgreSQL + Redis)
- Job runner for cron tasks
- Multiple web application servers
- Private network for secure internal communication
- Persistent volume for PostgreSQL

**Quick Start:**

1. **Provision infrastructure**:
   ```bash
   cd terraform/hetzner
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your Hetzner API token and SSH key
   terraform init
   terraform apply
   ```

2. **Configure Cloudflare CDN + SSL**:
   ```bash
   cd ../cloudflare
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with Cloudflare API token and server IP
   terraform init
   terraform apply
   # Download origin certificates from Cloudflare Dashboard
   # Save to ansible/certs/cloudflare.pem and ansible/certs/cloudflare.key
   ```

3. **Generate Ansible inventory**:
   ```bash
   cd ../hetzner
   terraform output -raw ansible_inventory > ../../ansible/hosts.yml
   ```

4. **Deploy with Ansible**:
   ```bash
   cd ../../
   just apb site
   ```

See [`terraform/hetzner/README.md`](terraform/hetzner/README.md) and [`terraform/cloudflare/README.md`](terraform/cloudflare/README.md) for complete setup instructions.

### Cloudflare CDN + SSL

Cloudflare is used for CDN, caching, and SSL/TLS termination. The Terraform configuration sets up:

- **CDN**: Caching for static assets (`/static/*`) and media files (`/media/*`)
- **SSL/TLS**: Full SSL mode with origin certificates
- **Security**: Firewall rules, DDoS protection, security headers
- **Performance**: HTTP/3, Brotli compression, early hints

**Requirements:**
1. Cloudflare account (free tier is sufficient)
2. Domain added to Cloudflare
3. Nameservers updated at your DNS provider (e.g., Namecheap)
4. Cloudflare origin certificates saved to `ansible/certs/`

**Origin Certificates:**

The Ansible deployment requires Cloudflare origin certificates:

1. Go to Cloudflare Dashboard → SSL/TLS → Origin Server
2. Click "Create Certificate"
3. Save the certificate as `ansible/certs/cloudflare.pem`
4. Save the private key as `ansible/certs/cloudflare.key`

These certificates are used for secure communication between Cloudflare and your origin server.

See [`terraform/cloudflare/README.md`](terraform/cloudflare/README.md) for detailed setup instructions.

### Environment Variables

Required for production:

```bash
ALLOWED_HOSTS=radiofeed.app
DATABASE_URL=postgresql://user:pass@host:5432/radiofeed
REDIS_URL=redis://host:6379/0
SECRET_KEY=<generate-with-manage-py-generate_secret_key>
ADMIN_URL=<random-path>/  # e.g., "my-secret-admin-path/"
ADMINS=admin@radiofeed.app
SENTRY_URL=https://...@sentry.io/...  # Optional
```

Optional (email via Mailgun):

```bash
EMAIL_HOST=mg.radiofeed.app
MAILGUN_API_KEY=<mailgun-api-key>
```

Optional (security headers):

```bash
USE_HSTS=true  # If load balancer doesn't set HSTS headers
```

### Docker Deployment

Build and run with Docker:

```bash
docker build -t radiofeed .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e REDIS_URL="redis://..." \
  -e SECRET_KEY="..." \
  radiofeed
```

### Kubernetes/K3s Deployment

Ansible playbooks are provided in the `ansible/` directory for K3s deployment. These work with the Terraform-provisioned infrastructure or manually created servers.

**Using with Terraform** (recommended):
```bash
# After terraform apply
cd terraform/hetzner
terraform output -raw ansible_inventory > ../../ansible/hosts.yml
cd ../../
just apb site
```

**Manual deployment**:
```bash
cd ansible
cp hosts.yml.example hosts.yml
# Edit hosts.yml with your server IPs
ansible-playbook -i hosts.yml site.yml
```

This sets up:
- K3s cluster with control plane and agent nodes
- PostgreSQL with persistent volume
- Redis for caching
- Django application with multiple replicas
- Traefik load balancer with SSL/TLS
- Automated cron jobs for feed parsing

See `ansible/README.md` for detailed deployment instructions.

### Post-Deployment

1. **Generate secret key**:
   ```bash
   python manage.py generate_secret_key
   ```

2. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

3. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

4. **Configure Site in admin**:
   - Visit `/admin/` (or your custom `ADMIN_URL`)
   - Update the default Site with your domain

5. **Set up cron jobs** for feed parsing:
   ```cron
   */15 * * * * /path/to/manage.py parse_feeds --limit 360
   0 9 * * * /path/to/manage.py send_notifications
   0 3 * * 0 /path/to/manage.py create_recommendations
   ```

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
