import functools
import itertools
import re
from collections.abc import Iterator
from typing import Final

from django.conf import settings
from django.http import HttpRequest
from django.template.defaultfilters import truncatechars
from django.templatetags.static import static
from django.urls import reverse

_RE_ANDROID_ICON: Final = r"^android-launchericon-([0-9]+)-([0-9]+).png"
_RE_IOS_ICON: Final = r"([0-9]+).png"


def get_manifest(request: HttpRequest) -> dict:
    """Returns PWA manifest."""
    start_url = reverse("index")

    categories = settings.PWA_CONFIG["manifest"]["categories"]
    description = settings.PWA_CONFIG["manifest"]["description"]
    background_color = settings.PWA_CONFIG["manifest"]["background_color"]

    return {
        "background_color": background_color,
        "theme_color": get_theme_color(),
        "description": description,
        "dir": "ltr",
        "display": "minimal-ui",
        "name": request.site.name,
        "short_name": truncatechars(request.site.name, 12),
        "prefer_related_applications": False,
        "orientation": "any",
        "scope": start_url,
        "start_url": start_url,
        "id": "?homescreen=1",
        "display_override": [
            "minimal-ui",
            "window-controls-overlay",
        ],
        "launch_handler": {
            "client_mode": [
                "focus-existing",
                "auto",
            ]
        },
        "categories": categories,
        "screenshots": [
            {
                "src": static("img/desktop.png"),
                "label": "Desktop homescreen",
                "form_factor": "wide",
                "type": "image/png",
            },
            {
                "src": static("img/mobile.png"),
                "label": "Mobile homescreen",
                "form_factor": "narrow",
                "type": "image/png",
            },
        ],
        "icons": _app_icons_list(),
        "shortcuts": [],
        "lang": "en",
    }


@functools.cache
def get_theme_color() -> str:
    """Returns theme color."""
    return settings.PWA_CONFIG["manifest"]["theme_color"]


@functools.cache
def get_assetlinks() -> list[dict]:
    """Return asset links."""

    package_name = settings.PWA_CONFIG["assetlinks"]["package_name"]
    fingerprints = settings.PWA_CONFIG["assetlinks"]["sha256_fingerprints"]

    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": package_name,
                "sha256_cert_fingerprints": fingerprints,
            },
        }
    ]


def _android_icons() -> Iterator[dict]:
    for filename in (settings.STATIC_SRC / "img" / "icons" / "android").iterdir():
        if matches := re.match(_RE_ANDROID_ICON, filename.name):
            size = matches[1]
            yield {"src": filename.name, "sizes": f"{size}x{size}"}


def _ios_icons() -> Iterator[dict]:
    for filename in (settings.STATIC_SRC / "img" / "icons" / "ios").iterdir():
        if matches := re.match(_RE_IOS_ICON, filename.name):
            size = matches[1]
            yield {"src": filename.name, "sizes": f"{size}x{size}"}


@functools.cache
def _app_icons_list() -> list[dict]:
    return list(_app_icons())


def _app_icons() -> Iterator[dict]:
    for icon in itertools.chain(_android_icons(), _ios_icons()):
        app_icon = icon | {
            "src": static(f"img/icons/{icon["src"]}"),
            "type": "image/png",
        }
        yield app_icon
        yield app_icon | {"purpose": "maskable"}
        yield app_icon | {"purpose": "any"}
