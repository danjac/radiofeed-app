import collections
import itertools
from collections.abc import Iterator

from django.db import transaction
from django_typer.management import Typer
from rich.progress import Progress

from radiofeed.episodes.models import AudioLog
from radiofeed.podcasts.models import Podcast, Subscription

app = Typer(help="Score podcasts based on various metrics")


@app.command()
def handle() -> None:
    """Score podcasts based on various metrics."""

    # Reset all scores to zero before recalculating
    Podcast.objects.filter(score__gt=0).update(score=0)

    # Prefetch subscription counts and listen counts

    sub_counts = collections.Counter(
        Subscription.objects.values_list("podcast", flat=True)
    )

    listen_counts = collections.Counter(
        AudioLog.objects.values_list("episode__podcast", flat=True)
    )

    podcast_ids = Podcast.objects.filter(
        active=True,
        private=False,
        pub_date__isnull=False,
    ).values_list("pk", flat=True)

    def _get_podcasts_for_update(podcast_ids: tuple[int]) -> Iterator[Podcast]:
        """Get podcasts for update."""
        for podcast in Podcast.objects.filter(pk__in=podcast_ids).select_for_update():
            score = 100 if podcast.promoted else 0

            score += sub_counts.get(podcast.pk, 0) * 10
            score += listen_counts.get(podcast.pk, 0) * 1

            if score:
                podcast.score = score
                yield podcast

    with Progress() as progress:
        task = progress.add_task(
            "[green]Scoring podcasts...",
            total=podcast_ids.count(),
        )

        for batch in itertools.batched(podcast_ids, 500, strict=False):
            with transaction.atomic():
                for_update = _get_podcasts_for_update(batch)
                Podcast.objects.bulk_update(for_update, ["score"])
            progress.update(task, advance=len(batch))
