from django.core.management.base import BaseCommand

from audiotrails.podcasts.models import Podcast
from audiotrails.podcasts.tasks import sync_podcast_feed, sync_podcast_feeds


class Command(BaseCommand):
    help = "Updates all podcasts from their RSS feeds."

    def add_arguments(self, parser):

        parser.add_argument(
            "--run-job",
            action="store_true",
            help="Just runs the sync_podcast_feeds celery task with no arguments",
        )

        parser.add_argument(
            "--no-pub-date",
            action="store_true",
            help="Updates only podcasts without a pub date",
        )

        parser.add_argument(
            "--use-celery",
            action="store_true",
            help="Sync each podcast using celery task",
        )

        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Force update",
        )

    def handle(self, *args, **options):

        if options["run_job"]:
            sync_podcast_feeds.delay()
            return

        podcasts = Podcast.objects.all()

        if options["no_pub_date"]:
            podcasts = podcasts.filter(pub_date__isnull=True)

        force_update = options["force_update"]

        for podcast in podcasts:
            if options["use_celery"]:
                self.stdout.write(f"Create sync task for {podcast}")
                sync_podcast_feed.delay(rss=podcast.rss, force_update=force_update)
            else:
                try:
                    sync_podcast_feed(rss=podcast.rss, force_update=force_update)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(str(e)))
