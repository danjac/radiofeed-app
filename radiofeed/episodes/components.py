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
        return "episodes/components/_episode.html"


component.registry.register(name="episode", component=EpisodeComponent)


class FavoriteToggleComponent(component.Component):
    def context(self, episode: Episode, is_favorited: bool) -> Dict:
        return {
            "episode": episode,
            "is_favorited": is_favorited,
        }

    def template(self, context: Dict) -> str:
        return "episodes/components/_favorite_toggle.html"


component.registry.register(name="favorite_toggle", component=FavoriteToggleComponent)


class QueueToggleComponent(component.Component):
    def context(self, episode: Episode, is_queued: bool) -> Dict:
        return {
            "episode": episode,
            "is_queued": is_queued,
        }

    def template(self, context: Dict) -> str:
        return "episodes/components/_queue_toggle.html"


component.registry.register(name="queue_toggle", component=QueueToggleComponent)


class PlayerToggleComponent(component.Component):
    def context(self, episode: Episode, is_playing: bool) -> Dict:
        return {
            "episode": episode,
            "is_playing": is_playing,
        }

    def template(self, context: Dict) -> str:
        return "episodes/components/_player_toggle.html"


component.registry.register(name="player_toggle", component=PlayerToggleComponent)
