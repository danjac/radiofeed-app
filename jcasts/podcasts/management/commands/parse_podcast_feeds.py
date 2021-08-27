from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Run podcast feed updates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Update all feeds (including unscheduled)",
        )

    def handle(self, *args, **options):

        num_feeds = feed_parser.parse_podcast_feeds(
            force_update=options["force_update"]
        )
        self.stdout.write(self.style.SUCCESS(f"{num_feeds} feed(s) to be pulled"))
