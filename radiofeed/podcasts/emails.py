from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader

from radiofeed.html import strip_html
from radiofeed.podcasts.models import Podcast


def send_recommendations_email(
    address: EmailAddress, num_podcasts: int = 6, **email_settings
) -> None:
    """Sends email to user with a list of recommended podcasts.

    Recommendations based on their subscriptions or promoted podcasts.

    Recommended podcasts are saved to the database, so the user is not recommended the same podcasts more than once.

    If no matching podcasts are found, no email is sent.
    """

    podcasts = (
        Podcast.objects.published()
        .recommended(address.user)
        .order_by(
            "-relevance",
            "-promoted",
            "-pub_date",
        )
    )[:num_podcasts]

    if podcasts:
        address.user.recommended_podcasts.add(*podcasts)

        html_message = loader.render_to_string(
            "podcasts/emails/recommendations.html",
            {
                "podcasts": podcasts,
                "recipient": address.user,
            },
        )

        name = address.user.first_name or address.user.username

        send_mail(
            f"Hi {name}, here are some new podcasts you might like!",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[address.email],
            message=strip_html(html_message),
            html_message=html_message,
            **email_settings,
        )
