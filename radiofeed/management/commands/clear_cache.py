import djclick as click
from django.conf import settings
from django.core.cache import caches
from django.core.cache.backends.base import InvalidCacheBackendError
from django.core.management.base import CommandError


@click.option(
    "--cache-names",
    "-c",
    multiple=True,
    help="Cache names to clear, if empty then clears all caches",
    default=[],
)
@click.option(
    "--no-input",
    is_flag=True,
    default=False,
    help="Do not ask for confirmation before clearing the cache.",
)
@click.command()
def command(*, cache_names: list[str], no_input: bool) -> None:
    """Deletes caches."""

    if not no_input:
        click.confirm("Are you sure you want to clear the cache?", abort=True)

    names = cache_names or settings.CACHES.keys()

    for name in names:
        click.echo(f"Clearing cache: {name}")
        try:
            cache = caches[name]
            cache.clear()
            click.secho(f"Cache '{name}' cleared", fg="green")
        except InvalidCacheBackendError as e:
            raise CommandError(f"Cache '{name}' does not exist") from e
