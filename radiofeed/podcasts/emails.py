from allauth.account.models import EmailAddress

from radiofeed.podcasts.models import Podcast
from radiofeed.users.emails import send_notification_email


def send_recommendations_email(recipient: EmailAddress, num_podcasts: int = 6) -> None:
    """Sends email to user with a list of recommended podcasts.

    Recommendations based on their subscriptions or promoted podcasts.

    Recommended podcasts are saved to the database, so the user is not recommended the same podcasts more than once.

    If no matching podcasts are found, no email is sent.
    """

    if podcasts := (
        Podcast.objects.published()
        .recommended(recipient.user)
        .order_by(
            "-relevance",
            "-promoted",
            "-pub_date",
        )
    )[:num_podcasts]:
        recipient.user.recommended_podcasts.add(*podcasts)

        send_notification_email(
            recipient,
            f"Hi, {recipient.user.name}, here are some podcasts you might like!",
            "podcasts/emails/recommendations.html",
            {
                "podcasts": podcasts,
            },
        )
