import typing

import djclick as click

from radiofeed.feedparser import opml_parser
from radiofeed.podcasts.models import Podcast


@click.command()
@click.argument("file", type=click.File("rb"))
def command(file: typing.BinaryIO) -> None:
    """Parses an OPML file and imports podcasts."""
    podcasts = Podcast.objects.bulk_create(
        [Podcast(rss=rss) for rss in opml_parser.parse_opml(file.read())],
        ignore_conflicts=True,
    )

    if num_podcasts := len(podcasts):
        click.secho(f"{num_podcasts} podcasts imported", fg="green")
    else:
        click.secho("No podcasts imported", fg="yellow")
