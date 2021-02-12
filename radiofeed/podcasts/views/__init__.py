from django.shortcuts import get_object_or_404

from ..models import Podcast


def get_podcast_or_404(podcast_id: int) -> Podcast:
    return get_object_or_404(Podcast, pk=podcast_id)
