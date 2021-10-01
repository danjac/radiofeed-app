from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Run podcast feed updates"

    def handle(self, *args, **options):
        num_feeds = feed_parser.parse_podcast_feeds()
        self.stdout.write(self.style.SUCCESS(f"{num_feeds} feed(s) to be pulled"))
