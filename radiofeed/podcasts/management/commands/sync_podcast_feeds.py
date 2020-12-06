# Django
from django.core.management.base import BaseCommand

# Third Party Libraries
import requests

# RadioFeed
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.rss_parser import RssParser


class Command(BaseCommand):
    help = "Updates all podcasts from their RSS feeds."

    def handle(self, *args, **options):
        for podcast in Podcast.objects.all():
            self.stdout.write(f"Syncing podcast {podcast}")
            try:
                RssParser.parse_from_podcast(podcast)
            except requests.HTTPError as e:
                self.stderr.write(str(e))
