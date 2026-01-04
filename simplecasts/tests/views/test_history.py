import pytest
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertTemplateUsed

from simplecasts.models import AudioLog
from simplecasts.tests.asserts import (
    assert200,
    assert404,
)
from simplecasts.tests.factories import (
    AudioLogFactory,
    EpisodeFactory,
    PodcastFactory,
)


class TestHistory:
    url = reverse_lazy("history:index")

    @pytest.mark.django_db
    def test_get(self, client, auth_user):
        AudioLogFactory.create_batch(33, user=auth_user)
        response = client.get(self.url)
        assert200(response)
        assertTemplateUsed(response, "history/index.html")

        assert200(response)
        assert len(response.context["page"].object_list) == 30

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        response = client.get(self.url)
        assert200(response)

    @pytest.mark.django_db
    def test_ascending(self, client, auth_user):
        AudioLogFactory.create_batch(33, user=auth_user)

        response = client.get(self.url, {"order": "asc"})
        assert200(response)

        assert len(response.context["page"].object_list) == 30

    @pytest.mark.django_db
    def test_search(self, client, auth_user):
        podcast = PodcastFactory(title="zzzz")

        for _ in range(3):
            AudioLogFactory(
                user=auth_user,
                episode=EpisodeFactory(title="zzzz", podcast=podcast),
            )

        AudioLogFactory(user=auth_user, episode=EpisodeFactory(title="testing"))
        response = client.get(self.url, {"search": "testing"})

        assert200(response)
        assert len(response.context["page"].object_list) == 1


class TestMarkAudioLogComplete:
    @pytest.mark.django_db
    def test_ok(self, client, auth_user, episode):
        audio_log = AudioLogFactory(user=auth_user, episode=episode, current_time=300)

        response = client.post(
            self.url(episode),
            headers={
                "HX-Request": "true",
                "HX-Target": "audio-log",
            },
        )

        assert200(response)

        audio_log.refresh_from_db()
        assert audio_log.current_time == 0

    @pytest.mark.django_db
    def test_is_playing(self, client, auth_user, player_episode):
        """Do not mark complete if episode is currently playing"""

        response = client.post(
            self.url(player_episode),
            headers={
                "HX-Request": "true",
                "HX-Target": "audio-log",
            },
        )

        assert404(response)

        assert AudioLog.objects.filter(user=auth_user, episode=player_episode).exists()

    def url(self, episode):
        return reverse("history:mark_complete", args=[episode.pk])


class TestRemoveAudioLog:
    @pytest.mark.django_db
    def test_ok(self, client, auth_user, episode):
        AudioLogFactory(user=auth_user, episode=episode)
        AudioLogFactory(user=auth_user)

        response = client.delete(
            self.url(episode),
            headers={
                "HX-Request": "true",
                "HX-Target": "audio-log",
            },
        )

        assert200(response)

        assert not AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=auth_user).count() == 1

    @pytest.mark.django_db
    def test_is_playing(self, client, auth_user, player_episode):
        """Do not remove log if episode is currently playing"""

        response = client.delete(
            self.url(player_episode),
            headers={
                "HX-Request": "true",
                "HX-Target": "audio-log",
            },
        )

        assert404(response)
        assert AudioLog.objects.filter(user=auth_user, episode=player_episode).exists()

    @pytest.mark.django_db
    def test_none_remaining(self, client, auth_user, episode):
        log = AudioLogFactory(user=auth_user, episode=episode)

        response = client.delete(
            self.url(log.episode),
            headers={
                "HX-Request": "true",
                "HX-Target": "audio-log",
            },
        )
        assert200(response)

        assert not AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=auth_user).count() == 0

    def url(self, episode):
        return reverse("history:remove", args=[episode.pk])
