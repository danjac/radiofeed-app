from __future__ import annotations

from django_rq import job

from radiofeed.podcasts import emails
from radiofeed.users.models import User


@job("emails")
def send_recommendations_email(user_id: int) -> None:
    """Sends recommendation email to user.

    Raises:
        UserDoesNotExist: if no matching recipient user found
    """
    emails.send_recommendations_email(
        User.objects.email_notification_recipients().get(pk=user_id)
    )
