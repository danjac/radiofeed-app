import typing

import djclick as click
from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from radiofeed.podcasts.models import Podcast


@click.command()
@click.argument("file", type=click.File("w"))
def command(file: typing.TextIO) -> None:
    """Export all podcasts to an OPML file."""
    podcasts = Podcast.objects.published().filter(private=False).order_by("title")

    file.write(
        render_to_string(
            "feedparser/podcasts.opml",
            {
                "podcasts": podcasts,
                "site": Site.objects.get_current(),
            },
        )
    )
