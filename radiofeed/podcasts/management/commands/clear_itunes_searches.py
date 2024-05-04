from datetime import timedelta

import djclick as click
from django.utils import timezone

from radiofeed.podcasts.models import ItunesSearch


@click.command(help="Delete old iTunes searches")
@click.option(
    "--hours", default=24, help="Delete iTunes searches run more than n hours ago"
)
def command(hours: int) -> None:
    """Implementation of command."""
    num_deleted, _ = ItunesSearch.objects.filter(
        completed__lt=timezone.now() - timedelta(hours=hours)
    ).delete()
    if num_deleted:
        click.echo(click.style(f"{num_deleted} searches deleted", bold=True))
