from typing import Dict, Optional

from django_components import component

from radiofeed.template.defaulttags import htmlattrs

from .models import CoverImage, Podcast


class PodcastComponent(component.Component):
    def context(self, podcast: Podcast, css_class: str = "", **attrs) -> Dict:
        return {
            "podcast": podcast,
            "podcast_url": podcast.get_absolute_url(),
            "css_class": css_class,
            "attrs": htmlattrs(attrs),
        }

    def template(self, context: Dict) -> str:
        return "podcasts/_podcast.html"


component.registry.register(name="podcast", component=PodcastComponent)


class CoverImageComponent(component.Component):
    def context(
        self,
        podcast: Podcast,
        lazy: bool = False,
        cover_image: Optional[CoverImage] = None,
        image_size: int = 20,
        css_class: str = "",
    ) -> Dict:
        """If cover_image is provided,  we don't need to lazy-load the image."""
        return {
            "podcast": podcast,
            "lazy": lazy and not (cover_image),
            "cover_image": cover_image,
            "image_size": image_size,
            "css_class": css_class,
        }

    def template(self, context: Dict) -> str:
        return "podcasts/_cover_image.html"


component.registry.register(name="cover_image", component=CoverImageComponent)
