from __future__ import annotations

import pytest

from django.urls import reverse, reverse_lazy

from jcasts.episodes.factories import EpisodeFactory
from jcasts.podcasts import itunes
from jcasts.podcasts.factories import (
    CategoryFactory,
    FollowFactory,
    PodcastFactory,
    RecommendationFactory,
)
from jcasts.podcasts.itunes import SearchResult
from jcasts.podcasts.models import Follow, Podcast
from jcasts.shared.assertions import assert_conflict, assert_ok

podcasts_url = reverse_lazy("podcasts:index")

mock_search_result = SearchResult(
    rss="http://example.com/test.xml",
    itunes="https://apple.com/some-link",
    image="test.jpg",
    title="test title",
)


def mock_fetch_itunes_genre(
    genre_id: int, num_results: int = 20
) -> tuple[list[SearchResult], list[Podcast]]:
    return [mock_search_result], [PodcastFactory()]


def mock_search_itunes(
    search_term: str, num_results: int = 12
) -> tuple[list[SearchResult], list[Podcast]]:
    return [mock_search_result], [PodcastFactory()]


class TestPodcasts:
    def test_anonymous(self, client, db):
        PodcastFactory.create_batch(3, promoted=True)
        resp = client.get(podcasts_url)
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_is_following_promoted(self, client, auth_user):
        """If user is not following any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        sub = FollowFactory(user=auth_user).podcast
        resp = client.get(reverse("podcasts:index"), {"promoted": True})
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3
        assert sub not in resp.context_data["page_obj"].object_list

    def test_user_is_not_following(self, client, auth_user):
        """If user is not following any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        resp = client.get(podcasts_url)
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_is_following(self, client, auth_user):
        """If user following any podcasts, show only own feed with these podcasts"""

        PodcastFactory.create_batch(3)
        sub = FollowFactory(user=auth_user)
        resp = client.get(podcasts_url)
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == sub.podcast


class TestSearchPodcasts:
    def test_search_empty(self, client, db):
        assert (
            client.get(
                reverse("podcasts:search_podcasts"),
                {"q": ""},
            ).url
            == podcasts_url
        )

    def test_search(self, client, db, faker):
        podcast = PodcastFactory(title=faker.unique.text())
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        resp = client.get(
            reverse("podcasts:search_podcasts"),
            {"q": podcast.title},
        )
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == podcast


class TestPodcastRecommendations:
    def test_get(self, client, db, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        resp = client.get(
            reverse("podcasts:podcast_recommendations", args=[podcast.id, podcast.slug])
        )
        assert_ok(resp)
        assert resp.context_data["podcast"] == podcast
        assert len(resp.context_data["recommendations"]) == 3


class TestPodcastDetail:
    def test_get_podcast(self, client, podcast):
        resp = client.get(
            reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
        )
        assert_ok(resp)
        assert resp.context_data["podcast"] == podcast


class TestPodcastEpisodes:
    def test_get_episodes(self, client, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)

        resp = client.get(
            reverse(
                "podcasts:podcast_episodes",
                args=[podcast.id, podcast.slug],
            )
        )
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self, client, podcast, faker):
        EpisodeFactory.create_batch(3, podcast=podcast)

        episode = EpisodeFactory(title=faker.unique.name(), podcast=podcast)

        resp = client.get(
            reverse(
                "podcasts:podcast_episodes",
                args=[podcast.id, podcast.slug],
            ),
            {"q": episode.title},
        )
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestDiscover:
    url = reverse_lazy("podcasts:categories")

    @pytest.fixture
    def parents(self, db):
        return CategoryFactory.create_batch(3, parent=None)

    def test_get(self, client, parents):

        c1 = CategoryFactory(parent=parents[0])
        c2 = CategoryFactory(parent=parents[1])
        c3 = CategoryFactory(parent=parents[2])

        PodcastFactory(categories=[c1, parents[0]])
        PodcastFactory(categories=[c2, parents[1]])
        PodcastFactory(categories=[c3, parents[2]])

        resp = client.get(self.url)
        assert_ok(resp)
        assert len(resp.context_data["categories"]) == 3

    def test_search(self, client, parents, faker):

        name = faker.unique.name()

        c1 = CategoryFactory(parent=parents[0])
        c2 = CategoryFactory(parent=parents[1])
        c3 = CategoryFactory(parent=parents[2], name=f"{name} child")
        c4 = CategoryFactory(name=f"{name} parent")

        PodcastFactory(categories=[c1])
        PodcastFactory(categories=[c2])
        PodcastFactory(categories=[c3])
        PodcastFactory(categories=[c4])

        resp = client.get(self.url, {"q": name})
        assert_ok(resp)
        assert len(resp.context_data["categories"]) == 2


class TestCategoryDetail:
    def test_get(self, client, category):
        CategoryFactory.create_batch(3, parent=category)
        PodcastFactory.create_batch(12, categories=[category])
        resp = client.get(category.get_absolute_url())
        assert_ok(resp)
        assert resp.context_data["category"] == category

    def test_get_episodes(self, client, category):

        CategoryFactory.create_batch(3, parent=category)
        PodcastFactory.create_batch(12, categories=[category])
        resp = client.get(category.get_absolute_url())
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 12

    def test_search(self, client, category, faker):

        CategoryFactory.create_batch(3, parent=category)
        PodcastFactory.create_batch(
            12, title="zzzz", keywords="zzzz", categories=[category]
        )
        podcast = PodcastFactory(title=faker.unique.text(), categories=[category])

        resp = client.get(category.get_absolute_url(), {"q": podcast.title})
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestFollow:
    @pytest.fixture
    def url(self, podcast):
        return reverse("podcasts:follow", args=[podcast.id])

    def test_follow(self, client, podcast, auth_user, url):
        resp = client.post(url)
        assert_ok(resp)
        assert Follow.objects.filter(podcast=podcast, user=auth_user).exists()

    @pytest.mark.django_db(transaction=True)
    def test_already_following(self, client, podcast, auth_user, url):
        FollowFactory(user=auth_user, podcast=podcast)
        resp = client.post(url)
        assert_conflict(resp)
        assert Follow.objects.filter(podcast=podcast, user=auth_user).exists()


class TestUnfollow:
    def test_unfollow(self, client, auth_user, podcast):
        FollowFactory(user=auth_user, podcast=podcast)
        resp = client.delete(reverse("podcasts:unfollow", args=[podcast.id]))
        assert_ok(resp)
        assert not Follow.objects.filter(podcast=podcast, user=auth_user).exists()


class TestITunesCategory:
    @pytest.fixture
    def category_with_itunes(self, db):
        return CategoryFactory(itunes_genre_id=1200)

    @pytest.fixture
    def url(self, category_with_itunes):
        return reverse("podcasts:itunes_category", args=[category_with_itunes.id])

    def test_get(self, client, mocker, category_with_itunes, url):

        mocker.patch("jcasts.podcasts.views.parse_feed.delay", autospec=True)
        mocker.patch.object(itunes, "fetch_itunes_genre", mock_fetch_itunes_genre)

        resp = client.get(url)

        assert_ok(resp)
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 1
        assert resp.context_data["results"][0].title == mock_search_result.title

    def test_invalid_results(self, client, mocker, category_with_itunes, url):

        mocker.patch.object(
            itunes, "fetch_itunes_genre", side_effect=itunes.Invalid, autospec=True
        )

        resp = client.get(url)

        assert_ok(resp)
        assert resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0


class TestSearchITunes:
    url = reverse_lazy("podcasts:search_itunes")

    def test_search_is_empty(self, client, db):
        resp = client.get(self.url)
        assert_ok(resp)

        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0

    def test_search(self, client, mocker, db):
        mock_parse = mocker.patch(
            "jcasts.podcasts.views.parse_feed.delay", autospec=True
        )
        mocker.patch.object(itunes, "search_itunes", mock_search_itunes)

        resp = client.get(self.url, {"q": "test"})

        assert_ok(resp)
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 1

        assert resp.context_data["results"][0].title == mock_search_result.title

        mock_parse.assert_called()

    def test_invalid_results(self, client, mocker, db):
        mocker.patch.object(
            itunes, "search_itunes", side_effect=itunes.Invalid, autospec=True
        )
        resp = client.get(self.url, {"q": "testing"})
        assert_ok(resp)
        assert resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0
