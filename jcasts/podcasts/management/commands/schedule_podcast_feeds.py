from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Enqueue podcast feeds"

    def handle(self, *args, **options):
        for podcast in Podcast.objects.filter(active=True):
            feed_parser.reschedule(podcast)
