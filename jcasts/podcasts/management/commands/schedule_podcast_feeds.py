from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def handle(self, *args, **options) -> None:

        Podcast.objects.filter(frequency__isnull=False).update(frequency=None)

        for_update = []
        now = timezone.now()

        for counter, podcast in enumerate(
            Podcast.objects.active()
            .fresh()
            .published()
            .order_by("-pub_date")
            .iterator()
        ):

            podcast.frequency, podcast.frequency_modifier = scheduler.schedule(
                list(podcast.episode_set.values_list("pub_date", flat=True)), 1.0
            )

            parsed = podcast.pub_date

            while parsed < now:

                podcast.frequency, podcast.frequency_modifier = scheduler.reschedule(
                    podcast.frequency,
                    podcast.frequency_modifier,
                )

                parsed += podcast.frequency

            podcast.parsed = parsed

            self.stdout.write(f"{counter}:{podcast.title}")

            for_update.append(podcast)

        Podcast.objects.bulk_update(
            for_update,
            fields=["frequency", "parsed"],
            batch_size=500,
        )
