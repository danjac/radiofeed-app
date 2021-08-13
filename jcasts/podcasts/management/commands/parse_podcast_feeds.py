from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Run podcast feed updates"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--force-update",
            action="store_true",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Set limit",
        )

    def handle(self, *args, **options) -> None:

        num_feeds = feed_parser.parse_scheduled_feeds(
            force_update=options["force_update"], limit=options["limit"]
        )
        self.stdout.write(self.style.SUCCESS(f"{num_feeds} feed(s) to be pulled"))
