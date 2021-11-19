from __future__ import annotations

from django.core.management.base import BaseCommand

from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Re-schedule podcast feeds"

    def handle(self, *args, **options) -> None:
        podcasts = (
            Podcast.objects.active()
            .filter(pub_date__isnull=False, queued__isnull=True)
            .order_by("-pub_date")
        )
        for_update = []

        for podcast in podcasts.iterator():
            pub_dates = list(podcast.episode_set.values_list("pub_date", flat=True))
            (
                podcast.scheduled,
                podcast.frequency,
                podcast.frequency_modifier,
            ) = scheduler.schedule(podcast.pub_date, pub_dates)

            self.stdout.write(
                f"Podcast {podcast.title}: {podcast.scheduled} {podcast.frequency}"
            )

            for_update.append(podcast)

        Podcast.objects.bulk_update(
            for_update,
            fields=[
                "frequency",
                "frequency_modifier",
                "scheduled",
            ],
            batch_size=500,
        )
        self.stdout.write(self.style.SUCCESS(f"{len(for_update)} podcasts updated"))
