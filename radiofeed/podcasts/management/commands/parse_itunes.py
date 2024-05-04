from concurrent.futures import wait
from datetime import timedelta

import djclick as click
import httpx
from django.utils import timezone

from radiofeed.client import get_client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import ItunesSearch
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor


@click.command(help="Parse saved iTunes searches")
def command() -> None:
    """Runs Itunes search for all saved searches. Any over 24 hours old are deleted."""
    client = get_client()

    searches = ItunesSearch.objects.filter(completed__isnull=True)

    with DatabaseSafeThreadPoolExecutor() as executor:
        wait(
            executor.db_safe_map(
                lambda search: _do_search(search, client),
                searches,
            )
        )

    now = timezone.now()

    searches.update(completed=now)

    # Delete any searches > 24 hours

    num_deleted, _ = ItunesSearch.objects.filter(
        completed__lt=now - timedelta(hours=24)
    ).delete()

    if num_deleted:
        click.echo(f"{num_deleted} search(es) deleted")


def _do_search(search: ItunesSearch, client: httpx.Client) -> None:
    try:
        feeds = itunes.search(client, search.search)
        click.echo(
            click.style(
                f"Search for '{search.search}': {len(feeds)} feed(s)",
                bold=True,
                fg="green",
            ),
        )
    except httpx.HTTPError as e:
        click.echo(
            click.style(
                f"Error for '{search.search}': {e}",
                bold=True,
                fg="red",
            ),
        )
