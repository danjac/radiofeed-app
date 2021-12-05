from __future__ import annotations

from django.core.management.base import BaseCommand

from jcasts.websub import subscriber


class Command(BaseCommand):
    help = "Renew out-of-date Websub subscriptions"

    def handle(self, *args, **options) -> None:
        subscriber.renew()
