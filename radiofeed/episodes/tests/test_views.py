import http
from datetime import timedelta

import pytest
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from pytest_django.asserts import assertContains, assertNotContains, assertTemplateUsed

from radiofeed.episodes.middleware import PlayerDetails
from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.episodes.tests.factories import (
    AudioLogFactory,
    BookmarkFactory,
    EpisodeFactory,
)
from radiofeed.podcasts.tests.factories import PodcastFactory, SubscriptionFactory
from radiofeed.tests.asserts import assert200, assert401, assert404

_index_url = reverse_lazy("episodes:index")


@pytest.fixture
def player_episode(auth_user, client, episode):
    AudioLogFactory(user=auth_user, episode=episode)

    session = client.session
    session[PlayerDetails.session_id] = episode.pk
    session.save()

    return episode


class TestIndex:
    @pytest.mark.django_db
    def test_no_episodes(self, client, auth_user):
        response = client.get(_index_url)
        assert200(response)
        assert len(response.context["page"].object_list) == 0

    @pytest.mark.django_db
    def test_has_no_subscriptions(self, client, auth_user):
        EpisodeFactory.create_batch(3)
        response = client.get(_index_url)

        assert200(response)
        assert len(response.context["page"].object_list) == 0

    @pytest.mark.django_db
    def test_has_subscriptions(self, client, auth_user):
        episode = EpisodeFactory()
        SubscriptionFactory(subscriber=auth_user, podcast=episode.podcast)

        response = client.get(_index_url)

        assert200(response)
        assert len(response.context["page"].object_list) == 1


class TestSearchEpisodes:
    url = reverse_lazy("episodes:search_episodes")

    @pytest.mark.django_db
    def test_search(self, auth_user, client, faker):
        EpisodeFactory.create_batch(3, title="zzzz", keywords="zzzz")
        episode = EpisodeFactory(title=faker.unique.name())
        response = client.get(self.url, {"search": episode.title})
        assert200(response)
        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == episode

    @pytest.mark.django_db
    def test_search_no_results(self, auth_user, client):
        response = client.get(self.url, {"search": "zzzz"})
        assert200(response)
        assert len(response.context["page"].object_list) == 0

    @pytest.mark.django_db
    def test_search_value_empty(self, auth_user, client):
        response = client.get(self.url, {"search": ""})
        assert response.url == _index_url


class TestEpisodeDetail:
    @pytest.fixture
    def episode(self, faker):
        return EpisodeFactory(
            podcast=PodcastFactory(
                owner=faker.name(),
                website=faker.url(),
                funding_url=faker.url(),
                funding_text=faker.text(),
                keywords=faker.text(),
                explicit=True,
            ),
            episode_type="full",
            season=1,
            episode=3,
            length=9000,
            duration="3:30:30",
        )

    @pytest.mark.django_db
    def test_ok(self, client, auth_user, episode):
        response = client.get(episode.get_absolute_url())
        assert200(response)
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
        assert response.context["episode"] == episode

        assertContains(response, "Remove episode from your History")
        assertContains(response, "Listened")

    @pytest.mark.django_db
    def test_no_prev_next_episode(self, client, auth_user, episode):
        response = client.get(episode.get_absolute_url())

        assert200(response)
        assert response.context["episode"] == episode
        assertNotContains(response, "No More Episodes")

    @pytest.mark.django_db
    def test_no_next_episode(self, client, auth_user, episode):
        EpisodeFactory(
            podcast=episode.podcast, pub_date=episode.pub_date - timedelta(days=30)
        )
        response = client.get(episode.get_absolute_url())
        assert200(response)
        assert response.context["episode"] == episode
        assertContains(response, "Last Episode")

    @pytest.mark.django_db
    def test_no_previous_episode(self, client, auth_user, episode):
        EpisodeFactory(
            podcast=episode.podcast, pub_date=episode.pub_date + timedelta(days=30)
        )
        response = client.get(episode.get_absolute_url())
        assert200(response)
        assert response.context["episode"] == episode
        assertContains(response, "First Episode")


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

        assert response.status_code == http.HTTPStatus.NO_CONTENT

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

        assert player_episode.pk not in client.session


class TestPlayerTimeUpdate:
    url = reverse_lazy("episodes:player_time_update")

    @pytest.mark.django_db
    def test_is_running(self, client, player_episode):
        response = client.post(
            self.url,
            {"current_time": "1030"},
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT

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
            {"current_time": "1030"},
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT

        log = AudioLog.objects.first()
        assert log is not None

        assert log.current_time == 1030
        assert log.episode == episode

    @pytest.mark.django_db
    def test_player_not_in_session(self, client, auth_user, episode):
        response = client.post(
            self.url,
            {"current_time": "1030"},
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT

        assert not AudioLog.objects.exists()

    @pytest.mark.django_db
    def test_missing_data(self, client, auth_user, player_episode):
        response = client.post(self.url)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST

    @pytest.mark.django_db
    def test_invalid_data(self, client, auth_user, player_episode):
        response = client.post(self.url, {"current_time": "xyz"})
        assert response.status_code == http.HTTPStatus.BAD_REQUEST

    @pytest.mark.django_db
    def test_user_not_authenticated(self, client):
        response = client.post(self.url, {"current_time": "1000"})
        assert401(response)


class TestBookmarks:
    url = reverse_lazy("episodes:bookmarks")

    @pytest.mark.django_db
    def test_get(self, client, auth_user):
        BookmarkFactory.create_batch(33, user=auth_user)

        response = client.get(self.url)

        assert200(response)
        assertTemplateUsed(response, "episodes/bookmarks.html")

        assert len(response.context["page"].object_list) == 30

    @pytest.mark.django_db
    def test_ascending(self, client, auth_user):
        BookmarkFactory.create_batch(33, user=auth_user)

        response = client.get(self.url, {"order": "asc"})

        assert200(response)
        assert len(response.context["page"].object_list) == 30

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        response = client.get(self.url)
        assert200(response)

    @pytest.mark.django_db
    def test_search(self, client, auth_user):
        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            BookmarkFactory(
                user=auth_user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        BookmarkFactory(user=auth_user, episode=EpisodeFactory(title="testing"))

        response = client.get(self.url, {"search": "testing"})

        assert200(response)
        assertTemplateUsed(response, "episodes/bookmarks.html")

        assert len(response.context["page"].object_list) == 1


class TestAddBookmark:
    @pytest.mark.django_db
    def test_post(self, client, auth_user, episode):
        response = client.post(self.url(episode), headers={"HX-Request": "true"})

        assert200(response)
        assert Bookmark.objects.filter(user=auth_user, episode=episode).exists()

    @pytest.mark.django_db()(transaction=True)
    def test_already_bookmarked(self, client, auth_user, episode):
        BookmarkFactory(episode=episode, user=auth_user)

        response = client.post(self.url(episode), headers={"HX-Request": "true"})
        assert response.status_code == http.HTTPStatus.CONFLICT

        assert Bookmark.objects.filter(user=auth_user, episode=episode).exists()

    def url(self, episode):
        return reverse("episodes:add_bookmark", args=[episode.pk])


class TestRemoveBookmark:
    @pytest.mark.django_db
    def test_post(self, client, auth_user, episode):
        BookmarkFactory(user=auth_user, episode=episode)
        response = client.delete(
            reverse("episodes:remove_bookmark", args=[episode.pk]),
            headers={"HX-Request": "true"},
        )
        assert200(response)

        assert not Bookmark.objects.filter(user=auth_user, episode=episode).exists()


class TestHistory:
    url = reverse_lazy("episodes:history")

    @pytest.mark.django_db
    def test_get(self, client, auth_user):
        AudioLogFactory.create_batch(33, user=auth_user)
        response = client.get(self.url)
        assert200(response)
        assertTemplateUsed(response, "episodes/history.html")

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
        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            AudioLogFactory(
                user=auth_user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        AudioLogFactory(user=auth_user, episode=EpisodeFactory(title="testing"))
        response = client.get(self.url, {"search": "testing"})

        assert200(response)
        assert len(response.context["page"].object_list) == 1


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
        return reverse("episodes:remove_audio_log", args=[episode.pk])
