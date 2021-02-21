from typing import Dict

from django_components import component

from radiofeed.template.defaulttags import htmlattrs

from .models import Podcast


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
