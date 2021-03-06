from typing import Dict, Optional

from django import template

from ..models import CoverImage, Podcast

register = template.Library()


@register.simple_tag
def get_promoted_podcasts(limit: int):
    return Podcast.objects.filter(pub_date__isnull=False, promoted=True).order_by(
        "-pub_date"
    )[:limit]


@register.inclusion_tag("podcasts/_cover_image.html")
def cover_image(
    podcast: Podcast,
    lazy: bool = False,
    cover_image: Optional[CoverImage] = None,
    size: str = "16",
    css_class: str = "",
    **attrs,
) -> Dict:
    if not lazy and cover_image is None:
        cover_image = podcast.get_cover_image_thumbnail()

    return {
        "podcast": podcast,
        "lazy": lazy and not (cover_image),
        "cover_image": cover_image,
        "css_class": css_class,
        "img_size": size,
        "attrs": attrs,
    }
