import functools
import itertools
import pathlib
from collections.abc import Iterator
from typing import TypedDict

from django.conf import settings
from django.http import HttpRequest
from django.template.defaultfilters import truncatechars
from django.templatetags.static import static
from django.urls import reverse
from PIL import Image


class ImageInfo(TypedDict):
    """Metadata icon or image info."""

    src: str
    sizes: str
    type: str


def get_manifest(request: HttpRequest) -> dict:
    """Returns PWA manifest."""

    manifest = settings.PWA_CONFIG["manifest"]

    background_color = manifest["background_color"]
    categories = manifest["categories"]
    description = manifest["description"]

    start_url = reverse("index")

    return {
        "background_color": background_color,
        "categories": categories,
        "description": description,
        "dir": "ltr",
        "display": "minimal-ui",
        "icons": _app_icons_list(),
        "id": "?homescreen=1",
        "lang": "en",
        "name": request.site.name,
        "orientation": "any",
        "prefer_related_applications": False,
        "scope": start_url,
        "shortcuts": [],
        "short_name": truncatechars(request.site.name, 12),
        "start_url": start_url,
        "theme_color": get_theme_color(),
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
    }


@functools.cache
def get_theme_color() -> str:
    """Returns theme color."""
    return settings.PWA_CONFIG["manifest"]["theme_color"]


@functools.cache
def get_assetlinks() -> list[dict]:
    """Return asset links."""

    assetlinks = settings.PWA_CONFIG["assetlinks"]

    package_name = assetlinks["package_name"]
    fingerprints = assetlinks["sha256_fingerprints"]

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


def _app_icons() -> Iterator[dict]:
    for icon in itertools.chain(_generate_icons("android"), _generate_icons("ios")):
        yield icon | {}
        yield icon | {"purpose": "maskable"}
        yield icon | {"purpose": "any"}


def _generate_icons(dir: str) -> Iterator[ImageInfo]:
    path = pathlib.Path("img") / "icons" / dir
    for filename in (settings.STATIC_SRC / path).glob("*.png"):
        yield ImageInfo(
            src=static(f"{path}/{filename.name}"),
            sizes=_icon_size(filename),
            type="image/png",
        )


@functools.cache
def _icon_size(path: pathlib.Path) -> str:
    return "{}x{}".format(*Image.open(path).size)
