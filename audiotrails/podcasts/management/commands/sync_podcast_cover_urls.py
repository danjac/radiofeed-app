from django.core.management.base import BaseCommand

from audiotrails.podcasts.models import Podcast
from audiotrails.podcasts.tasks import sync_podcast_cover_url


class Command(BaseCommand):
    help = "Updates all podcasts from their RSS feeds."

    def handle(self, *args, **options) -> None:

        podcasts = Podcast.objects.filter(cover_url__isnull=True)
        self.stdout.write(f"{podcasts.count()} podcasts to process")
        for podcast in podcasts:
            sync_podcast_cover_url.delay(podcast.id)
