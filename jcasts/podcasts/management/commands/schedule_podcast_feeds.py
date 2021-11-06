from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from jcasts.episodes.models import Episode
from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options) -> None:
        for_update = []
        now = timezone.now()
        for podcast in Podcast.objects.active().published().iterator():

            self.stdout.write(podcast.title)

            pub_dates = list(
                Episode.objects.filter(podcast=podcast).values_list(
                    "pub_date", flat=True
                )
            )

            podcast.frequency = scheduler.calc_frequency(pub_dates)
            podcast.polled = now - podcast.frequency

            for_update.append(podcast)

        Podcast.objects.bulk_update(for_update, fields=["frequency", "polled"])
