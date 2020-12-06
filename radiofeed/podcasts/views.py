# Django
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

# Local
from .models import Podcast


def podcast_list(request):
    """Shows list of podcasts"""

    podcasts = Podcast.objects.filter(pub_date__isnull=False).order_by("-pub_date")
    return TemplateResponse(request, "podcasts/index.html", {"podcasts": podcasts})


def podcast_detail(request, podcast_id, slug=None):
    podcast = get_object_or_404(Podcast, pk=podcast_id)
    episodes = podcast.episode_set.order_by("-pub_date")
    return TemplateResponse(
        request, "podcasts/detail.html", {"podcast": podcast, "episodes": episodes}
    )
