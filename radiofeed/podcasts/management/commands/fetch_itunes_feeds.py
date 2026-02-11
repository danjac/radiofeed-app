import dataclasses
import itertools

from django.core.management import CommandError, CommandParser
from django.core.management.base import BaseCommand

from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Category
from radiofeed.podcasts.tasks import fetch_itunes_feeds


@dataclasses.dataclass(kw_only=True, frozen=True)
class Result:
    """Result of fetching iTunes feeds for a country."""

    country: str
    category: Category | None = None

    feeds: list[itunes.Feed] = dataclasses.field(default_factory=list)
    error: itunes.ItunesError | None = None


class Command(BaseCommand):
    """Fetch the top iTunes podcasts for a given country."""

    help = "Fetch the top iTunes podcasts for a given country."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments to the management command."""
        parser.add_argument(
            "--countries",
            "-c",
            default=itunes.COUNTRIES,
            nargs="+",
        )

    def handle(self, *, countries: list[str], **options) -> None:
        """Handle the management command."""

        # Check countries are in list of supported countries by iTunes
        if invalid := (set(countries) - set(itunes.COUNTRIES)):
            raise CommandError(f"Invalid iTunes country codes: {', '.join(invalid)}")

        genre_ids = Category.objects.filter(itunes_genre_id__isnull=False).values_list(
            "itunes_genre_id", flat=True
        )
        combinations = itertools.product(countries, (None, *genre_ids))

        for country, genre_id in combinations:
            fetch_itunes_feeds.enqueue(country=country, genre_id=genre_id)
