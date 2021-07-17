import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jcasts.config.settings.local")

app = Celery("jcasts")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request}")


@app.task(bind=True)
def clear_sessions(self):
    from django.core.management import call_command  # noqa

    call_command("clearsessions")
