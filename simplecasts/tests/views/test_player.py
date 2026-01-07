import json

import pytest
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertContains

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
    EpisodeFactory,
)


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
