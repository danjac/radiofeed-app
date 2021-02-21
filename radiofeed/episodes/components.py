from typing import Dict, Optional

from django.urls import reverse

from django_components import component

from radiofeed.podcasts.models import CoverImage
from radiofeed.template.defaulttags import htmlattrs

from .models import Episode


class EpisodeComponent(component.Component):
    def context(
        self,
        episode: Episode,
        dom_id: str = "",
        podcast_url: str = "",
        actions_url: str = "",
        cover_image: Optional[CoverImage] = None,
        **attrs,
    ) -> Dict:
        return {
            "episode": episode,
            "podcast": episode.podcast,
            "dom_id": dom_id or episode.get_dom_id(),
            "duration": episode.get_duration_in_seconds(),
            "actions_url": actions_url
            or reverse("episodes:actions", args=[episode.id]),
            "episode_url": episode.get_absolute_url(),
            "podcast_url": podcast_url or episode.podcast.get_absolute_url(),
            "cover_image": cover_image,
            "attrs": htmlattrs(attrs),
        }

    def template(self, context: Dict) -> str:
        return "episodes/_episode.html"


component.registry.register(name="episode", component=EpisodeComponent)
