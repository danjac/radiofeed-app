# Standard Library
import os

# Third Party Libraries
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "radiofeed.config.settings.local")

app = Celery("radiofeed")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request}")
