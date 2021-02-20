from typing import Dict

from django.urls import reverse

from django_components import component

from radiofeed.template.defaulttags import htmlattrs

from .models import Episode


class EpisodeComponent(component.Component):
    def context(
        self,
        episode: Episode,
        dom_id: str = "",
        actions_url: str = "",
        css_class: str = "",
        **attrs
    ) -> Dict:
        return {
            "episode": episode,
            "episode_url": episode.get_absolute_url(),
            "dom_id": dom_id or episode.get_dom_id(),
            "css_class": css_class,
            "duration": episode.get_duration_in_seconds(),
            "podcast": episode.podcast,
            "actions_url": actions_url
            or reverse("episodes:actions", args=[episode.id]),
            "attrs": htmlattrs(attrs),
        }

    def template(self, context: Dict) -> str:
        return "episodes/_episode.html"


component.registry.register(name="episode", component=EpisodeComponent)
