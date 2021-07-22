from django.core.management.base import BaseCommand

from jcasts.podcasts.tasks import create_podcast_recommendations


class Command(BaseCommand):
    help = "Updates all podcasts from their RSS feeds."

    def handle(self, *args, **options) -> None:
        create_podcast_recommendations.delay()
