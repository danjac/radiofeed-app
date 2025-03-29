import djclick as click

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
@click.option(
    "--promote/--no-promote",
    help="Promote podcasts",
    default=True,
    is_flag=True,
)
def command(**options):
    """Crawl iTunes Top Chart."""
    for podcast in itunes.fetch_chart(get_client(), **options):
        click.secho(str(podcast), fg="green")
