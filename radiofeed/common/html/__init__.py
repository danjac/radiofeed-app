# Standard Library
import html

# Third Party Libraries
import bleach

cleaner = bleach.Cleaner(tags=bleach.ALLOWED_TAGS + ["p", "div", "br"], strip=True)


def linkify_callback(attrs, new=False):
    attrs[(None, "target")] = "_blank"
    attrs[(None, "rel")] = "noopener noreferrer nofollow"
    return attrs


def clean_html_content(value):
    try:
        return bleach.linkify(cleaner.clean(value), [linkify_callback]) if value else ""
    except (ValueError, TypeError):
        return ""


def stripentities(value):
    """Removes any HTML entities such as &nbsp; and replaces
    them with plain ASCII equivalents."""
    return html.unescape(value)
