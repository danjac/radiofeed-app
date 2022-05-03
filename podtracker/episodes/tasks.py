from __future__ import annotations

from datetime import timedelta

from podtracker.episodes.emails import send_new_episodes_email
from podtracker.users.models import User


def send_new_episodes_emails(since: timedelta = timedelta(days=7)):
    for user in User.objects.filter(send_email_notifications=True, is_active=True):
        send_new_episodes_email(user, since)
