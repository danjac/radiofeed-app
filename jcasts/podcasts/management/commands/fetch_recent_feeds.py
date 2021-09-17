from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import podcastindex


class Command(BaseCommand):
    help = "Fetch new feeds from Podcast Index"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
        )

        parser.add_argument(
            "--since", type=int, default=1, help="Hours since feeds last updated"
        )

    def handle(self, *args, **options):
        feeds = podcastindex.recent_feeds(
            limit=options["limit"], since=timedelta(hours=options["since"])
        )
        self.stdout.write(self.style.SUCCESS(f"{len(feeds)} feed(s) updated"))
