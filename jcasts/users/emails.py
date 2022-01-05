import pathlib

from functools import lru_cache

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template import loader

from jcasts.shared.typedefs import User


def send_user_notification_email(
    user: User,
    subject: str,
    template_name: str,
    html_template_name: str,
    context: dict | None = None,
) -> None:

    if not user.send_email_notifications:
        return

    site = Site.objects.get_current()

    context = {
        "recipient": user,
        "site": site,
        "inline_css": get_inline_css(),
    } | (context or {})

    send_mail(
        f"[{site.name}] {subject}",
        loader.render_to_string(template_name, context),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=loader.render_to_string(html_template_name, context),
    )


@lru_cache
def get_inline_css() -> str:
    try:
        return open(
            pathlib.Path(settings.BASE_DIR) / "assets" / "bundle.css", "r"
        ).read()
    except IOError:
        return ""
