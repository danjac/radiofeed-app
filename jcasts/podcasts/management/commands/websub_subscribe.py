from django.core.management.base import BaseCommand

from jcasts.podcasts import websub


class Command(BaseCommand):
    help = "Subscribe podcasts to websub"

    def handle(self, *args, **options):
        for podcast_id in websub.get_podcasts().values_list("pk", flat=True).iterator():
            websub.subscribe.delay(podcast_id)
