from concurrent.futures import wait

import djclick as click
import httpx
from django.utils import timezone

from radiofeed.client import get_client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import ItunesSearch
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor


@click.command(help="Parse saved iTunes searches")
def command() -> None:
    """Runs Itunes search for all saved searches."""
    client = get_client()

    with DatabaseSafeThreadPoolExecutor() as executor:
        wait(
            executor.db_safe_map(
                lambda search: _do_search(search, client),
                ItunesSearch.objects.filter(completed__isnull=True),
            )
        )


def _do_search(search: ItunesSearch, client: httpx.Client) -> None:
    try:
        click.echo(f"Searching for {search.search}...")
        for feed in itunes.search(client, search.search):
            click.echo(
                click.style(
                    f"Found {feed.title}",
                    bold=True,
                    fg="green",
                ),
            )
        search.completed = timezone.now()
        search.save()
    except httpx.HTTPError as e:
        click.echo(
            click.style(
                f"Error for '{search.search}': {e}",
                bold=True,
                fg="red",
            ),
        )
