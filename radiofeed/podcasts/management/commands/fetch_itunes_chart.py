import djclick as click

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes


@click.command()
@click.option(
    "--country",
    "-c",
    help="Country code",
    default=itunes.Country.UNITED_KINGDOM,
    type=click.Choice(itunes.get_countries()),
)
@click.option(
    "--promote/--no-promote",
    "-p",
    is_flag=True,
    help="Promote the podcast to the top of the chart",
    default=True,
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
    for podcast in itunes.fetch_chart(get_client(), **options):
        click.secho(str(podcast), fg="green")
