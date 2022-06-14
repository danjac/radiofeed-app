from celery import shared_task

from radiofeed.podcasts import feed_updater


@shared_task
def update_podcast_feed(podcast_id: int):
    feed_updater.update(podcast_id)
