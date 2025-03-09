import djclick as click
from django.core.management.base import CommandError

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes


@click.command()
@click.option(
    "--country",
    "-c",
    type=str,
    help="iTunes country",
    default="gb",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    help="Limit the number of podcasts to fetch",
    default=30,
)
def command(**options):
    """Crawl iTunes Top Chart."""
    try:
        for podcast in itunes.fetch_chart(get_client(), **options):
            click.secho(str(podcast), fg="green")
    except itunes.ItunesError as e:
        raise CommandError from e
