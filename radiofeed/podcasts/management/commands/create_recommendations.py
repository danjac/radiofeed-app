from django.core.management.base import BaseCommand

from radiofeed.podcasts import recommender


class Command(BaseCommand):
    help = """
    Runs recommendation algorithm.
    """

    def handle(self, *args, **options):
        recommender.recommend()
