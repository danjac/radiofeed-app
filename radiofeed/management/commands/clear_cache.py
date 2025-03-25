import djclick as click
from django.conf import settings
from django.core.cache import caches


@click.command()
def command() -> None:
    """Deletes caches."""

    for name in settings.CACHES:
        click.echo(f"Clearing cache: {name}")
        cache = caches[name]
        cache.clear()
        click.secho(f"Cache '{name}' cleared", fg="green")
