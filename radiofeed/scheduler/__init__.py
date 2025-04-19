from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from django.conf import settings

scheduler = BlockingScheduler(
    executors={
        "default": ThreadPoolExecutor(20),
        "processpool": ProcessPoolExecutor(5),
    },
    timezone=settings.TIME_ZONE,
)
