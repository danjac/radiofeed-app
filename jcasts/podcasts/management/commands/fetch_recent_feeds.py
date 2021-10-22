from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser, podcastindex
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Fetch recent feeds from Podcast Index"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
        )

        parser.add_argument(
            "--since", type=int, default=24, help="Hours since new feeds added"
        )

    def handle(self, *args, **options):
        for_update = []
        feeds = [
            feed
            for feed in podcastindex.recent_feeds(
                limit=options["limit"], since=timedelta(hours=options["since"])
            )
            if feed.podcast and feed.podcast.active
        ]
        for feed in feeds:
            self.stdout.write(f"{feed.podcast.title} [{feed.podcast.rss}]")
            feed_parser.parse_podcast_feed(feed.podcast.rss)
            feed.podcast.indexed = True
            for_update.append(feed.podcast)

        Podcast.objects.bulk_update(for_update, fields=["indexed"])

        self.stdout.write(self.style.SUCCESS(f"{len(feeds)} feed(s) updated"))
