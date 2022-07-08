from __future__ import annotations

from huey.contrib.djhuey import db_task

from radiofeed.podcasts import emails
from radiofeed.users.models import User


@db_task()
def send_recommendations_email(user_id: int) -> None:
    """Sends recommendation email to user.

    Raises:
        UserDoesNotExist: if no matching recipient user found
    """
    emails.send_recommendations_email(
        User.objects.email_notification_recipients().get(pk=user_id)
    )
