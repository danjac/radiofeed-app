import functools
import itertools
import pathlib
from collections.abc import Iterator

from django.conf import settings
from django.http import HttpRequest
from django.template.defaultfilters import truncatechars
from django.templatetags.static import static
from django.urls import reverse
from PIL import Image


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


@functools.cache
def _app_icons_list() -> list[dict]:
    return list(_app_icons())


@functools.cache
def _icon_size(path: pathlib.Path) -> tuple[int, int]:
    return Image.open(path).size


def _app_icons() -> Iterator[dict]:
    for icon in itertools.chain(_generate_icons("android"), _generate_icons("ios")):
        yield icon
        yield icon | {"purpose": "maskable"}
        yield icon | {"purpose": "any"}


def _generate_icons(dir: str) -> Iterator[dict[str, str]]:
    path = pathlib.Path("img") / "icons" / dir
    for filename in (settings.STATIC_SRC / path).glob("*.png"):
        width, height = _icon_size(filename)
        yield {
            "src": static(path / filename.name),
            "sizes": f"{width}x{height}",
            "type": "image/png",
        }
