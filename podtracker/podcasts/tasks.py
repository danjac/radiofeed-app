from celery import shared_task

from podtracker.podcasts import recommender, scheduler


@shared_task
def recommend():
    return recommender.recommend()


@shared_task
def schedule_primary_feeds():
    return scheduler.schedule_primary_feeds()


@shared_task
def schedule_secondary_feeds():
    return scheduler.schedule_secondary_feeds()
