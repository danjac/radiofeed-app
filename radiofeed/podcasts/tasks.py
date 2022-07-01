from huey.contrib.djhuey import db_task

from radiofeed.podcasts import emails
from radiofeed.users.models import User


@db_task()
def send_recommendations_email(user_id):
    """Sends recommendation email to user.

    Args:
        user_id (int): User PK

    Raises:
        UserDoesNotExist: if no matching recipient user found
    """
    emails.send_recommendations_email(
        User.objects.email_notification_recipients().get(pk=user_id)
    )
