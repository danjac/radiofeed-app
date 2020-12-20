# Django
from django.core.management.base import BaseCommand

# RadioFeed
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Category, Podcast


class Command(BaseCommand):
    help = "Fetches top iTunes results from API for each category and adds new podcasts to database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=100, help="Max results from iTunes API",
        )

    def handle(self, *args, **options):

        categories = (
            Category.objects.filter(itunes_genre_id__isnull=False)
            .prefetch_related("podcast_set")
            .order_by("name")
        )

        for category in categories:
            current = category.podcast_set.values_list("itunes", flat=True)
            podcasts = []

            try:
                results = itunes.fetch_itunes_genre(
                    category.itunes_genre_id, num_results=options["limit"]
                )
            except (itunes.Invalid, itunes.Timeout) as e:
                self.stderr.write(self.style.ERROR(str(e)))
                continue

            podcasts = [
                Podcast(title=result.title, rss=result.rss, itunes=result.itunes)
                for result in [r for r in results if r.itunes not in current]
            ]

            Podcast.objects.bulk_create(podcasts, ignore_conflicts=True)

            if podcasts:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{category.name}: {len(podcasts)} new podcast(s)"
                    )
                )
