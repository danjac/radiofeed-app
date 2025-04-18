import functools
import urllib.parse

from allauth.account.models import EmailAddress
from django.core.mail import EmailMultiAlternatives
from django.core.signing import TimestampSigner
from django.db.models import QuerySet
from django.template import loader

from radiofeed.html import strip_html
from radiofeed.templatetags import absolute_uri


def send_notification_email(
    recipient: EmailAddress,
    subject: str,
    template_name: str,
    context: dict | None = None,
    *,
    headers: dict | None = None,
    **kwargs,
) -> None:
    """Sends an email to the given recipient."""
    unsubscribe_url = get_unsubscribe_url(recipient.email)

    html_content = loader.render_to_string(
        template_name,
        context={
            "recipient": recipient.user,
            "unsubscribe_url": unsubscribe_url,
        }
        | (context or {}),
    )

    headers = {"<List-Unsubscribe>": f"<{unsubscribe_url}>"} | (headers or {})

    msg = EmailMultiAlternatives(
        subject=subject,
        body=strip_html(html_content),
        to=[recipient.email],
        **kwargs,
    )

    msg.attach_alternative(html_content, "text/html")
    msg.send()


def get_recipients() -> QuerySet[EmailAddress]:
    """Get recipients for email notifications.

    If `addresses` is provided, filter by list of email addresses.
    """
    return EmailAddress.objects.filter(
        user__is_active=True,
        user__send_email_notifications=True,
        primary=True,
        verified=True,
    ).select_related("user")


@functools.cache
def get_unsubscribe_signer() -> TimestampSigner:
    """Get the signer for unsubscribe links."""
    return TimestampSigner(salt="unsubscribe")


def get_unsubscribe_url(email: str) -> str:
    """Generate an unsubscribe URL for the given email address."""
    return (
        absolute_uri("users:unsubscribe")
        + "?"
        + urllib.parse.urlencode(
            {
                "email": get_unsubscribe_signer().sign(email),
            }
        )
    )
