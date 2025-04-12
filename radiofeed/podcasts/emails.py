import urllib.parse

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.signing import Signer
from django.template import loader

from radiofeed.html import strip_html
from radiofeed.podcasts.models import Podcast
from radiofeed.templatetags import absolute_uri


def send_recommendations_email(address: EmailAddress, num_podcasts: int = 6) -> None:
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

        unsubscribe_url = (
            absolute_uri("users:unsubscribe")
            + "?"
            + urllib.parse.urlencode(
                {
                    "email": Signer().sign(address.email),
                }
            )
        )

        html_message = loader.render_to_string(
            "podcasts/emails/recommendations.html",
            {
                "podcasts": podcasts,
                "recipient": address.user,
                "unsubscribe_url": unsubscribe_url,
            },
        )

        name = address.user.first_name or address.user.username

        msg = EmailMultiAlternatives(
            subject=f"Hi {name}, here are some new podcasts you might like!",
            body=strip_html(html_message),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[address.email],
            headers={
                "List-Unsubscribe": f"<{unsubscribe_url}>",
            },
        )

        msg.attach_alternative(html_message, "text/html")

        msg.send()
