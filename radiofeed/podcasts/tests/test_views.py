# Third Party Libraries
# Django
from django.urls import reverse

import pytest

# RadioFeed
from radiofeed.episodes.factories import EpisodeFactory

# Local
from .. import views
from ..factories import CategoryFactory, PodcastFactory

pytestmark = pytest.mark.django_db


class TestPodcastList:
    def test_get(self, rf):
        PodcastFactory.create_batch(3)
        resp = views.podcast_list(rf.get(reverse("podcasts:podcast_list")))
        assert resp.status_code == 200
        assert len(resp.context_data["podcasts"]) == 3


class TestPodcastDetail:
    def test_get(self, rf, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        resp = views.podcast_detail(
            rf.get(podcast.get_absolute_url()), podcast.id, podcast.slug
        )
        assert resp.status_code == 200
        assert resp.context_data["podcast"] == podcast
        assert len(resp.context_data["episodes"]) == 3


class TestCategoryList:
    def test_get(self, rf):
        parents = CategoryFactory.create_batch(3, parent=None)
        CategoryFactory(parent=parents[0])
        CategoryFactory(parent=parents[1])
        CategoryFactory(parent=parents[2])
        resp = views.category_list(rf.get(reverse("podcasts:category_list")))
        assert resp.status_code == 200
        assert len(resp.context_data["categories"]) == 3


class TestCategoryDetail:
    def test_get(self, rf, category):

        CategoryFactory.create_batch(3, parent=category)
        PodcastFactory.create_batch(12, categories=[category])

        resp = views.category_detail(
            rf.get(category.get_absolute_url()), category.id, category.slug
        )
        assert resp.status_code == 200
        assert resp.context_data["category"] == category
        assert len(resp.context_data["podcasts"]) == 12
