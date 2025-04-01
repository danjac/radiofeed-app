import djclick as click
from django.conf import settings
from django.core.cache import caches


@click.command()
@click.option(
    "--cache-names",
    "-c",
    multiple=True,
    default=[],
    help="Cache names to clear (default: ALL)",
)
def clear_cache(cache_names: list[str]) -> None:
    """Clear cache(s)"""
    cache_names = cache_names or settings.CACHES.keys()
    click.secho(f"Clearing caches: {', '.join(cache_names)}", fg="blue")
    for cache_name in cache_names:
        cache = caches[cache_name]
        cache.clear()
        click.secho(f"Cleared cache {cache_name}", fg="green")
