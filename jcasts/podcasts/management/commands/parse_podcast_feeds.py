from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Run podcast feed updates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
        )

    def handle(self, *args, **options):
        num_feeds = feed_parser.parse_podcast_feeds(options["limit"])
        self.stdout.write(self.style.SUCCESS(f"{num_feeds} feed(s) to be pulled"))
