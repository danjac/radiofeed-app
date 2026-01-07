from datetime import timedelta

import json
import pytest
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from pytest_django.asserts import assertContains, assertNotContains, assertTemplateUsed

from simplecasts.middleware import PlayerDetails
from simplecasts.models import AudioLog
from simplecasts.tests.asserts import (
    assert200,
    assert204,
    assert400,
    assert401,
    assert409,
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


class TestSearchEpisodes:
    url = reverse_lazy("episodes:search_episodes")

    @pytest.mark.django_db
    def test_search(self, auth_user, client, faker):
        EpisodeFactory.create_batch(3, title="zzzz")
        episode = EpisodeFactory(title=faker.unique.name())
        response = client.get(self.url, {"search": episode.title})
        assert200(response)
        assertTemplateUsed(response, "search/search_episodes.html")
        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == episode

    @pytest.mark.django_db
    def test_search_no_results(self, auth_user, client):
        response = client.get(self.url, {"search": "zzzz"})
        assert200(response)
        assertTemplateUsed(response, "search/search_episodes.html")
        assert len(response.context["page"].object_list) == 0

    @pytest.mark.django_db
    def test_search_value_empty(self, auth_user, client):
        response = client.get(self.url, {"search": ""})
        assert response.url == _index_url


class TestStartPlayer:
    @pytest.mark.django_db
    def test_play_from_start(self, client, auth_user, episode):
        response = client.post(
            self.url(episode),
            headers={
                "HX-Request": "true",
                "HX-Target": "audio-player-button",
            },
        )
        assert200(response)
        assertContains(response, 'id="audio-player-button"')

        assert AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert client.session[PlayerDetails.session_id] == episode.pk

    @pytest.mark.django_db
    def test_another_episode_in_player(self, client, auth_user, player_episode):
        episode = EpisodeFactory()
        response = client.post(
            self.url(episode),
            headers={
                "HX-Request": "true",
                "HX-Target": "audio-player-button",
            },
        )

        assert200(response)
        assertContains(response, 'id="audio-player-button"')

        assert AudioLog.objects.filter(user=auth_user, episode=episode).exists()

        assert client.session[PlayerDetails.session_id] == episode.pk

    @pytest.mark.django_db
    def test_resume(self, client, auth_user, player_episode):
        response = client.post(
            self.url(player_episode),
            headers={
                "HX-Request": "true",
                "HX-Target": "audio-player-button",
            },
        )

        assert200(response)
        assertContains(response, 'id="audio-player-button"')

        assert client.session[PlayerDetails.session_id] == player_episode.pk

    def url(self, episode):
        return reverse("episodes:start_player", args=[episode.pk])


class TestClosePlayer:
    url = reverse_lazy("episodes:close_player")

    @pytest.mark.django_db
    def test_player_empty(self, client, auth_user, episode):
        response = client.post(
            self.url,
            headers={
                "HX-Request": "true",
                "HX-Target": "audio-player-button",
            },
        )

        assert204(response)

    @pytest.mark.django_db
    def test_close(
        self,
        client,
        player_episode,
    ):
        response = client.post(
            self.url,
            headers={
                "HX-Request": "true",
                "HX-Target": "audio-player-button",
            },
        )

        assert200(response)
        assertContains(response, 'id="audio-player-button"')

        assert player_episode.pk not in client.session


class TestPlayerTimeUpdate:
    url = reverse_lazy("episodes:player_time_update")

    @pytest.mark.django_db
    def test_is_running(self, client, player_episode):
        response = client.post(
            self.url,
            json.dumps(
                {
                    "current_time": 1030,
                    "duration": 3600,
                }
            ),
            content_type="application/json",
        )

        assert200(response)

        log = AudioLog.objects.first()
        assert log is not None

        assert log.current_time == 1030

    @pytest.mark.django_db
    def test_player_log_missing(self, client, auth_user, episode):
        session = client.session
        session[PlayerDetails.session_id] = episode.pk
        session.save()

        response = client.post(
            self.url,
            json.dumps(
                {
                    "current_time": 1030,
                    "duration": 3600,
                }
            ),
            content_type="application/json",
        )

        assert200(response)

        log = AudioLog.objects.get()

        assert log.current_time == 1030
        assert log.episode == episode

    @pytest.mark.django_db
    def test_player_not_in_session(self, client, auth_user, episode):
        response = client.post(
            self.url,
            json.dumps(
                {
                    "current_time": 1030,
                    "duration": 3600,
                }
            ),
            content_type="application/json",
        )

        assert400(response)

        assert not AudioLog.objects.exists()

    @pytest.mark.django_db
    def test_missing_data(self, client, auth_user, player_episode):
        response = client.post(self.url)
        assert400(response)

    @pytest.mark.django_db
    def test_invalid_data(self, client, auth_user, player_episode):
        response = client.post(
            self.url,
            json.dumps(
                {
                    "current_time": "xyz",
                    "duration": "abc",
                }
            ),
            content_type="application/json",
        )
        assert400(response)

    @pytest.mark.django_db()(transaction=True)
    def test_episode_does_not_exist(self, client, auth_user):
        session = client.session
        session[PlayerDetails.session_id] = 12345
        session.save()

        response = client.post(
            self.url,
            json.dumps(
                {
                    "current_time": 1000,
                    "duration": 3600,
                }
            ),
            content_type="application/json",
        )
        assert409(response)

    @pytest.mark.django_db
    def test_user_not_authenticated(self, client):
        response = client.post(
            self.url,
            json.dumps(
                {
                    "current_time": 1000,
                    "duration": 3600,
                }
            ),
            content_type="application/json",
        )
        assert401(response)
