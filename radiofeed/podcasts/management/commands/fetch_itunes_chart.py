import djclick as click

from radiofeed.http_client import Client, get_client
from radiofeed.podcasts import itunes
from radiofeed.thread_pool import execute_thread_pool


@click.command()
@click.option(
    "--promote",
    "-p",
    help="Countries to promote",
    multiple=True,
    type=click.Choice(itunes.get_countries()),
    default=[itunes.Country.UNITED_KINGDOM],
)
@click.option(
    "--limit",
    "-l",
    type=int,
    help="Limit the number of podcasts to fetch",
    default=100,
)
def command(promote: list[itunes.Country], limit: int):
    """Crawl iTunes Top Chart."""

    client = get_client()

    execute_thread_pool(
        lambda country: _fetch_itunes_chart(
            client,
            country=country,
            limit=limit,
            promote=promote,
        ),
        itunes.get_countries(),
    )


def _fetch_itunes_chart(
    client: Client,
    country: itunes.Country,
    limit: int,
    promote: list[itunes.Country],
):
    click.secho(f"Fetching iTunes chart for {country}...", fg="blue")
    try:
        for podcast in itunes.fetch_chart(
            client,
            country=country,
            limit=limit,
            promote=(country in promote),
        ):
            click.secho(str(podcast), fg="green")
    except itunes.ItunesError as e:
        click.secho(str(e), fg="red")
