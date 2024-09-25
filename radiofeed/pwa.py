import functools
import itertools
import pathlib
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


def _app_icons() -> Iterator[dict]:
    for icon in itertools.chain(
        _generate_icons("android", _re_android_icon()),
        _generate_icons("ios", _re_ios_icon()),
    ):
        yield icon
        yield icon | {"purpose": "maskable"}
        yield icon | {"purpose": "any"}


def _generate_icons(dir: str, pattern: re.Pattern) -> Iterator[dict[str, str]]:
    path = pathlib.Path("img") / "icons" / dir

    for filename in (settings.STATIC_SRC / path).iterdir():
        if matches := pattern.match(filename.name):
            size = matches[1]
            yield {
                "src": static(path / filename.name),
                "sizes": f"{size}x{size}",
                "type": "image/png",
            }


@functools.cache
def _app_icons_list() -> list[dict]:
    return list(_app_icons())


@functools.cache
def _re_ios_icon() -> re.Pattern:
    return re.compile(_RE_IOS_ICON)


@functools.cache
def _re_android_icon() -> re.Pattern:
    return re.compile(_RE_ANDROID_ICON)
