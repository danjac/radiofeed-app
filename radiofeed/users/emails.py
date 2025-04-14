import functools
import urllib.parse

from allauth.account.models import EmailAddress
from django.core.signing import TimestampSigner
from django.db.models import QuerySet

from radiofeed.templatetags import absolute_uri


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


def get_recipients() -> QuerySet[EmailAddress]:
    """Get recipients for email notifications."""
    return EmailAddress.objects.filter(
        user__is_active=True,
        user__send_email_notifications=True,
        primary=True,
        verified=True,
    ).select_related("user")
