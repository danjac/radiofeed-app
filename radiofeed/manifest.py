import functools
import itertools
from collections.abc import Iterator
from typing import Final, TypedDict

from django.conf import settings
from django.http import HttpRequest
from django.template.defaultfilters import truncatechars
from django.templatetags.static import static
from django.urls import reverse

_ANDROID_ICONS: Final = (
    512,
    192,
    144,
    96,
    72,
    48,
)

_IOS_ICONS: Final = (
    16,
    20,
    29,
    32,
    40,
    50,
    57,
    58,
    60,
    64,
    72,
    76,
    80,
    97,
    100,
    114,
    120,
    128,
    144,
    152,
    167,
    180,
    192,
    256,
    512,
    1024,
)


class Icon(TypedDict):
    """PWA icon info."""

    src: str
    sizes: str


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


def _android_icons() -> Iterator[Icon]:
    for size in _ANDROID_ICONS:
        yield Icon(
            src=f"src-android/android-launchericon-{size}-{size}.png",
            sizes=f"{size}x{size}",
        )


def _ios_icons() -> Iterator[Icon]:
    for size in _IOS_ICONS:
        yield Icon(
            src=f"ios/{size}.png",
            sizes=f"{size}x{size}",
        )


@functools.cache
def _app_icons_list() -> list[dict]:
    return list(_app_icons())


def _app_icons() -> Iterator[dict]:
    for icon in itertools.chain(_android_icons(), _ios_icons()):
        app_icon = icon | {
            "src": static(f"img/icons/{icon.src}"),
            "type": "image/png",
        }
        yield app_icon
        yield app_icon | {"purpose": "maskable"}
        yield app_icon | {"purpose": "any"}
