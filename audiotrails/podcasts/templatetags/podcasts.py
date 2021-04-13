from django import template

register = template.Library()


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
