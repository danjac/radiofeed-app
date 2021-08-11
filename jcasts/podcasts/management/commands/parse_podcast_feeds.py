from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Run podcast feed updates"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--sporadic", action="store_true", help="Run less frequent podcast feeds"
        )
        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Update all feeds (ignore scheduled times)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Set limit",
        )

    def handle(self, *args, **options) -> None:

        kwargs = {
            "force_update": options["force_update"],
            "limit": options["limit"],
        }

        if options["sporadic"]:
            num_feeds = feed_parser.parse_sporadic_feeds(**kwargs)
        else:
            num_feeds = feed_parser.parse_frequent_feeds(**kwargs)

        self.stdout.write(self.style.SUCCESS(f"{num_feeds} feed(s) to be pulled"))
