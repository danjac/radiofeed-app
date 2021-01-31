from django.core.management.base import BaseCommand, CommandParser

from radiofeed.podcasts import itunes


class Command(BaseCommand):
    help = "Fetches top iTunes results from API for each category and adds new podcasts to database"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Max results from iTunes API",
        )

    def handle(self, *args, **options) -> None:
        new_podcasts = itunes.crawl_itunes(options["limit"])

        if new_podcasts:
            self.stdout.write(self.style.SUCCESS(f"{new_podcasts} new podcast(s)"))
