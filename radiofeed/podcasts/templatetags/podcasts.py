from django import template
from django.db.models import QuerySet
from django.utils import timezone

from ..models import Podcast

register = template.Library()


@register.simple_tag
def get_promoted_podcasts(limit):
    return get_available_podcasts().filter(promoted=True).order_by("-pub_date")[:limit]


@register.inclusion_tag("podcasts/_cover_image.html")
def cover_image(
    podcast,
    lazy=False,
    cover_image=None,
    size="16",
    css_class="",
    **attrs,
):
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


def get_available_podcasts() -> QuerySet:
    return Podcast.objects.filter(
        pub_date__isnull=False, cover_image__isnull=False, pub_date__lt=timezone.now()
    ).exclude(cover_image="")
