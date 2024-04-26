from django.conf import settings
from django.core.mail import send_mail
from django.template import loader

from radiofeed.cleaners import strip_html


def send_email(
    subject: str,
    recipient_list: list[str],
    template: str,
    context: dict | None = None,
    *,
    from_email: str | None = None,
    **kwargs,
) -> int:
    """Sends email using Django template to build message and HTML content."""

    html_message = loader.render_to_string(template, context)

    return send_mail(
        subject,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        message=strip_html(html_message),
        html_message=html_message,
        **kwargs,
    )
