from __future__ import annotations

from django.core.management.base import BaseCommand

from podtracker.episodes.emails import send_new_episodes_emails


class Command(BaseCommand):
    help = "Email podcast recommendations to users"

    def handle(self, *args, **options) -> None:
        send_new_episodes_emails()
