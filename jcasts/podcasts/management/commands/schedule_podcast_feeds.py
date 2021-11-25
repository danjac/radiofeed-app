from __future__ import annotations

from django.core.management.base import BaseCommand

from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options) -> None:

        Podcast.objects.update(frequency=None)

        for_update = []

        for counter, podcast in enumerate(
            Podcast.objects.active()
            .published()
            .frequent()
            .order_by("-pub_date")
            .iterator()
        ):

            podcast.frequency, _ = scheduler.schedule(
                list(podcast.episode_set.values_list("pub_date", flat=True))
            )

            self.stdout.write(f"{counter}:{podcast.title}")

            for_update.append(podcast)

        Podcast.objects.bulk_update(
            for_update,
            fields=["frequency"],
            batch_size=500,
        )
