from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from django.conf import settings

scheduler = BlockingScheduler(
    executors={
        "default": ThreadPoolExecutor(),
    },
    timezone=settings.TIME_ZONE,
)
