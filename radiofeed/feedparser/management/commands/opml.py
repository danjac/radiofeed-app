from typing import Annotated

import typer
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django_typer.management import TyperCommand, command

from radiofeed.feedparser import opml_parser
from radiofeed.podcasts.models import Podcast


class Command(TyperCommand):
    """OPML management commands."""

    @command()
    def parse(
        self,
        file: Annotated[
            typer.FileBinaryRead, typer.Argument(help="OPML file to parse")
        ],
        *,
        promote: Annotated[
            bool, typer.Option(help="Promote all imported podcasts")
        ] = False,
    ) -> None:
        """Parses an OPML file and imports podcasts."""
        podcasts = Podcast.objects.bulk_create(
            [
                Podcast(
                    rss=rss,
                    promoted=promote,
                )
                for rss in opml_parser.parse_opml(file.read())
            ],
            ignore_conflicts=True,
        )

        if num_podcasts := len(podcasts):
            self.stdout.write(self.style.SUCCESS(f"{num_podcasts} podcasts imported"))
        else:
            self.stdout.write(self.style.ERROR("No podcasts found in OPML"))

    @command()
    def export(
        self,
        file: Annotated[typer.FileTextWrite, typer.Argument(help="OPML file to write")],
        *,
        promoted: Annotated[
            bool, typer.Option(help="Export only promoted podcasts")
        ] = False,
    ) -> None:
        """Exports all podcasts to an OPML file."""
        podcasts = Podcast.objects.published().filter(private=False).order_by("title")

        if promoted:
            podcasts = podcasts.filter(promoted=True)

        file.write(
            render_to_string(
                "feedparser/podcasts.opml",
                {
                    "podcasts": podcasts,
                    "site": Site.objects.get_current(),
                },
            )
        )
