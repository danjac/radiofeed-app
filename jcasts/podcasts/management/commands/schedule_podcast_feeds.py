from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options):
        feed_parser.schedule_podcast_feeds()
