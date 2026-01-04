from datetime import timedelta

import pytest
from django.urls import reverse_lazy
from django.utils import timezone
from pytest_django.asserts import assertContains, assertNotContains, assertTemplateUsed

from simplecasts.tests.asserts import (
    assert200,
)
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
    def test_no_prev_next_episode(self, client, auth_user, episode):
        response = client.get(episode.get_absolute_url())

        assert200(response)
        assertTemplateUsed(response, "episodes/detail.html")
        assert response.context["episode"] == episode
        assertNotContains(response, "No More Episodes")

    @pytest.mark.django_db
    def test_no_next_episode(self, client, auth_user, episode):
        EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date - timedelta(days=30),
        )
        response = client.get(episode.get_absolute_url())
        assert200(response)
        assertTemplateUsed(response, "episodes/detail.html")
        assert response.context["episode"] == episode
        assertContains(response, "Last Episode")

    @pytest.mark.django_db
    def test_no_previous_episode(self, client, auth_user, episode):
        EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date + timedelta(days=30),
        )
        response = client.get(episode.get_absolute_url())
        assert200(response)
        assertTemplateUsed(response, "episodes/detail.html")
        assert response.context["episode"] == episode
        assertContains(response, "First Episode")
