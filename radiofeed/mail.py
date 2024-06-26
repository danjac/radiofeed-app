from django.core.mail import send_mail
from django.template import loader

from radiofeed.html import strip_html


def send_templated_mail(
    subject: str,
    recipient_list: list[str],
    template: str,
    context: dict | None = None,
    from_email: str | None = None,
    **email_settings,
) -> int:
    """Sends email using Django template to build message and HTML content."""

    html_message = loader.render_to_string(template, context)

    return send_mail(
        subject,
        from_email=from_email,
        recipient_list=recipient_list,
        message=strip_html(html_message),
        html_message=html_message,
        **email_settings,
    )
