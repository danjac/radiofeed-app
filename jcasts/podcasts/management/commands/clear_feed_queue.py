from __future__ import annotations

from django.core.management.base import BaseCommand

from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = """
    Clears any podcasts stuck in the queue. This sometimes happens e.g. when
    restarting workers in a deployment.
    """

    def handle(self, *args, **options) -> None:
        Podcast.objects.filter(queued__isnull=False).update(queued=None)
