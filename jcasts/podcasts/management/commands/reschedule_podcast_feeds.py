from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Reschedule podcast feeds"

    def handle(self, *args, **options):
        feed_parser.reschedule_podcast_feeds()
