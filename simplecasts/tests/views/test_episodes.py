import pytest
from django.urls import reverse_lazy
from django.utils import timezone
from pytest_django.asserts import assertContains, assertTemplateUsed

from simplecasts.tests.asserts import assert200
from simplecasts.tests.factories import (
    AudioLogFactory,
    EpisodeFactory,
    PodcastFactory,
    SubscriptionFactory,
)

_index_url = reverse_lazy("episodes:index")


class TestNewReleases:
    @pytest.mark.django_db
    def test_no_episodes(self, client, auth_user):
        response = client.get(_index_url)
        assert200(response)
        assertTemplateUsed(response, "episodes/index.html")
        assert len(response.context["episodes"]) == 0

    @pytest.mark.django_db
    def test_has_no_subscriptions(self, client, auth_user):
        EpisodeFactory.create_batch(3)
        response = client.get(_index_url)

        assert200(response)
        assertTemplateUsed(response, "episodes/index.html")
        assert len(response.context["episodes"]) == 0

    @pytest.mark.django_db
    def test_has_subscriptions(self, client, auth_user):
        episode = EpisodeFactory()
        SubscriptionFactory(subscriber=auth_user, podcast=episode.podcast)

        response = client.get(_index_url)

        assert200(response)
        assertTemplateUsed(response, "episodes/index.html")
        assert len(response.context["episodes"]) == 1


class TestEpisodeDetail:
    @pytest.fixture
    def episode(self, faker):
        return EpisodeFactory(
            podcast=PodcastFactory(
                owner=faker.name(),
                website=faker.url(),
                funding_url=faker.url(),
                funding_text=faker.text(),
                explicit=True,
            ),
            episode_type="full",
            file_size=9000,
            duration="3:30:30",
        )

    @pytest.mark.django_db
    def test_ok(self, client, auth_user, episode):
        response = client.get(episode.get_absolute_url())
        assert200(response)
        assertTemplateUsed(response, "episodes/detail.html")
        assert response.context["episode"] == episode

    @pytest.mark.django_db
    def test_listened(self, client, auth_user, episode):
        AudioLogFactory(
            episode=episode,
            user=auth_user,
            current_time=900,
            listened=timezone.now(),
        )

        response = client.get(episode.get_absolute_url())

        assert200(response)
        assertTemplateUsed(response, "episodes/detail.html")
        assert response.context["episode"] == episode

        assertContains(response, "Remove episode from your History")
        assertContains(response, "Listened")

    @pytest.mark.django_db
    def test_bookmarked(self, client, auth_user, episode):
        from simplecasts.tests.factories import BookmarkFactory

        BookmarkFactory(user=auth_user, episode=episode)

        response = client.get(episode.get_absolute_url())
        assert200(response)

        assertContains(response, "Remove from Bookmarks")

    @pytest.mark.django_db
    def test_is_not_playing(self, client, auth_user, episode):
        response = client.get(episode.get_absolute_url())

        assert200(response)
        assertTemplateUsed(response, "episodes/detail.html")
        assert response.context["episode"] == episode

        assertContains(response, "Play")

    @pytest.mark.django_db
    def test_is_playing(self, client, auth_user, player_episode):
        response = client.get(player_episode.get_absolute_url())

        assert200(response)
        assertTemplateUsed(response, "episodes/detail.html")
        assert response.context["episode"] == player_episode

        assertContains(response, "Close Player")


class TestSearchEpisodes:
    url = reverse_lazy("episodes:search_episodes")

    @pytest.mark.django_db
    def test_search(self, client, auth_user):
        podcast = PodcastFactory()
        EpisodeFactory.create_batch(3, podcast=podcast, title="testing")
        EpisodeFactory.create_batch(3, podcast=podcast, title="xyz")
        response = client.get(self.url, {"search": "testing"})

        assert200(response)
        assertTemplateUsed(response, "episodes/search_episodes.html")

        assert len(response.context["page"].object_list) == 3

    @pytest.mark.django_db
    def test_redirect_no_search(self, client, auth_user):
        response = client.get(self.url)
        assert response.status_code == 302
        assert response.url == _index_url
