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

    # Prefetch subscription counts and listen counts

    sub_counts = collections.Counter(
        Subscription.objects.values_list("podcast", flat=True)
    )

    listen_counts = collections.Counter(
        AudioLog.objects.values_list("episode__podcast", flat=True)
    )

    # Reset all scores to zero before recalculating
    Podcast.objects.filter(score__gt=0).update(score=0)

    podcast_ids = Podcast.objects.filter(
        active=True,
        private=False,
        pub_date__isnull=False,
    ).values_list("pk", flat=True)

    with Progress() as progress:
        task = progress.add_task(
            "[green]Scoring podcasts...",
            total=podcast_ids.count(),
        )

        for batch in itertools.batched(podcast_ids, 500, strict=False):
            with transaction.atomic():
                for_update = _get_podcasts_for_update(
                    batch,
                    sub_counts=sub_counts,
                    listen_counts=listen_counts,
                )
                Podcast.objects.bulk_update(for_update, ["score"])
            progress.update(task, advance=len(batch))


def _get_podcasts_for_update(
    podcast_ids: tuple[int],
    *,
    sub_counts: dict[int, int],
    listen_counts: dict[int, int],
) -> Iterator[Podcast]:
    """Get podcasts for update."""
    podcasts = Podcast.objects.filter(pk__in=podcast_ids).select_for_update()
    for podcast in podcasts:
        score = 0

        if podcast.promoted:
            score += 100

        score += sub_counts.get(podcast.pk, 0) * 10
        score += listen_counts.get(podcast.pk, 0) * 1

        podcast.score = score

        if podcast.score:
            yield podcast
