from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler(
    executors={
        "default": ThreadPoolExecutor(20),
        "processpool": ProcessPoolExecutor(5),
    },
    timezone="UTC",
)
