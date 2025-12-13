import json

import pytest
from django.urls import reverse_lazy

from listenwave.audio_player.middleware import PlayerDetails
from listenwave.episodes.models import AudioLog
from listenwave.tests.asserts import (
    assert200,
    assert400,
    assert401,
    assert409,
)


class TestPlayerTimeUpdate:
    url = reverse_lazy("audio_player:player_time_update")

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
