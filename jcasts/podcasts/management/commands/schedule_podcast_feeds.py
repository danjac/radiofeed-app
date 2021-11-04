from __future__ import annotations

from django.core.management.base import BaseCommand

from jcasts.episodes.models import Episode
from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options) -> None:
        for podcast in Podcast.objects.active().iterator():
            pub_dates = list(
                Episode.objects.filter(podcast=podcast).values_list(
                    "pub_date", flat=True
                )
            )

            frequency = scheduler.calc_frequency(pub_dates)

            Podcast.objects.filter(pk=podcast.id).update(
                frequency=frequency,
                scheduled=scheduler.reschedule(frequency, podcast.pub_date),
            )

            self.stdout.write(podcast.title)
