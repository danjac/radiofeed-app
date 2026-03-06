import itertools

from django.conf import settings
from django.core.management import BaseCommand, CommandParser

from radiofeed.podcasts import tasks
from radiofeed.podcasts.models import Category


class Command(BaseCommand):
    """Django management command to fetch top iTunes podcasts for specified countries."""

    help = "Fetch the top iTunes podcasts for a given country."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command-line arguments for fetching iTunes podcasts."""
        parser.add_argument(
            "--countries",
            "-c",
            nargs="+",
            help="List of country codes to fetch iTunes podcasts for.",
        )

    def handle(self, *countries: str, **options) -> None:
        """Fetch the top iTunes podcasts for a given country."""
        unique_countries = set(countries or settings.ITUNES_COUNTRIES)

        self.stdout.write(
            f"Fetching iTunes podcasts for countries: {', '.join(unique_countries)}"
        )

        genre_ids = list(
            Category.objects.filter(itunes_genre_id__isnull=False)
            .values_list("itunes_genre_id", flat=True)
            .distinct()
        )

        # Create combinations of countries and genre IDs, including a None genre ID for fetching
        # most popular across all genres.
        combinations = itertools.product(unique_countries, (None, *genre_ids))

        self.stdout.write(
            f"Enqueuing tasks for {len(unique_countries)} countries and {len(genre_ids) + 1} genre combinations..."
        )

        for country, genre_id in combinations:
            tasks.fetch_itunes_feeds.enqueue(country=country, genre_id=genre_id)
