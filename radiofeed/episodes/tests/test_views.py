from __future__ import annotations

from datetime import timedelta

import pytest

from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertContains, assertNotContains

from radiofeed.common.asserts import (
    assert_bad_request,
    assert_conflict,
    assert_no_content,
    assert_ok,
)
from radiofeed.common.factories import create_batch
from radiofeed.episodes.factories import (
    create_audio_log,
    create_bookmark,
    create_episode,
)
from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.episodes.player import Player
from radiofeed.podcasts.factories import create_podcast, create_subscription

episodes_url = reverse_lazy("episodes:index")


@pytest.fixture
def player_episode(client, episode):
    session = client.session
    session[Player.session_key] = episode.id
    session.save()
    return episode


def is_player_episode(client, episode):
    return client.session.get(Player.session_key) == episode.id


class TestNewEpisodes:
    def test_no_episodes(self, client, auth_user):
        response = client.get(episodes_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 0

    def test_not_subscribed(self, client, auth_user):
        promoted = create_podcast(promoted=True)
        create_episode(podcast=promoted)
        create_batch(create_episode, 3)
        response = client.get(episodes_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    def test_user_has_subscribed(self, client, auth_user):
        promoted = create_podcast(promoted=True)
        create_episode(podcast=promoted)

        create_batch(create_episode, 3)

        episode = create_episode()
        create_subscription(subscriber=auth_user, podcast=episode.podcast)

        response = client.get(episodes_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == episode
        assert not response.context["promoted"]
        assert response.context["has_subscriptions"]

    def test_user_has_subscribed_promoted(self, client, auth_user):
        promoted = create_podcast(promoted=True)
        create_episode(podcast=promoted)

        create_batch(create_episode, 3)

        episode = create_episode()
        create_subscription(subscriber=auth_user, podcast=episode.podcast)

        response = client.get(episodes_url, {"promoted": True})

        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0].podcast == promoted
        assert response.context["promoted"]
        assert response.context["has_subscriptions"]


class TestSearchEpisodes:
    url = reverse_lazy("episodes:search_episodes")

    def test_no_results(self, auth_user, client):
        response = client.get(self.url, {"query": "test"})
        assert_ok(response)

    def test_search_empty(self, auth_user, client):
        assert client.get(self.url, {"query": ""}).url == episodes_url

    def test_search(self, auth_user, client, faker):
        create_batch(create_episode, 3, title="zzzz", keywords="zzzz")
        episode = create_episode(title=faker.unique.name())
        response = client.get(self.url, {"query": episode.title})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == episode

    def test_search_no_results(self, auth_user, client, faker):
        response = client.get(self.url, {"query": "zzzz"})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 0


class TestEpisodeDetail:
    @pytest.fixture
    def episode(self, db, faker):
        return create_episode(
            podcast=create_podcast(
                owner=faker.name(),
                link=faker.url(),
                funding_url=faker.url(),
                funding_text=faker.text(),
                keywords=faker.text(),
            ),
            episode_type="full",
            season=1,
            episode=3,
            length=9000,
            duration="3:30:30",
        )

    @pytest.fixture
    def prev_episode(self, auth_user, episode):
        return create_episode(
            podcast=episode.podcast, pub_date=episode.pub_date - timedelta(days=7)
        )

    @pytest.fixture
    def next_episode(self, auth_user, episode):
        return create_episode(
            podcast=episode.podcast, pub_date=episode.pub_date + timedelta(days=7)
        )

    def test_authenticated(
        self,
        client,
        auth_user,
        episode,
        prev_episode,
        next_episode,
    ):
        response = client.get(episode.get_absolute_url())
        assert_ok(response)
        assert response.context["episode"] == episode

    def test_listened(
        self,
        client,
        auth_user,
        episode,
        prev_episode,
        next_episode,
    ):
        create_audio_log(episode=episode, user=auth_user, current_time=900)

        response = client.get(episode.get_absolute_url())
        assert_ok(response)

        assert response.context["episode"] == episode

        assertContains(response, "Remove episode from your History")
        assertContains(response, "Listened")

    def test_no_prev_next_episde(
        self,
        client,
        auth_user,
        episode,
    ):
        response = client.get(episode.get_absolute_url())
        assert_ok(response)
        assert response.context["episode"] == episode
        assertNotContains(response, "No More Episodes")

    def test_no_next_episode(
        self,
        client,
        auth_user,
        episode,
    ):
        create_episode(
            podcast=episode.podcast, pub_date=episode.pub_date - timedelta(days=30)
        )
        response = client.get(episode.get_absolute_url())
        assert_ok(response)
        assert response.context["episode"] == episode
        assertContains(response, "No More Episodes")

    def test_no_previous_episode(
        self,
        client,
        auth_user,
        episode,
    ):
        create_episode(
            podcast=episode.podcast, pub_date=episode.pub_date + timedelta(days=30)
        )
        response = client.get(episode.get_absolute_url())
        assert_ok(response)
        assert response.context["episode"] == episode
        assertContains(response, "No More Episodes")


class TestStartPlayer:
    # we have a number of savepoints here adding to query count
    num_savepoints = 3

    def url(self, episode):
        return reverse("episodes:start_player", args=[episode.id])

    def test_play_from_start(self, client, db, auth_user, episode):
        assert_ok(
            client.post(
                self.url(episode),
                HTTP_HX_TARGET="audio-player",
                HTTP_HX_REQUEST="true",
            ),
        )

        assert AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert is_player_episode(client, episode)

    def test_another_episode_in_player(self, client, auth_user, episode):
        client.session[Player.session_key] = create_episode().id

        assert_ok(
            client.post(
                self.url(episode),
                HTTP_HX_TARGET="audio-player",
                HTTP_HX_REQUEST="true",
            ),
        )

        assert AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert is_player_episode(client, episode)

    def test_resume(self, client, auth_user, episode):
        log = create_audio_log(user=auth_user, episode=episode, current_time=2000)
        assert_ok(
            client.post(
                self.url(episode),
                HTTP_HX_TARGET="audio-player",
                HTTP_HX_REQUEST="true",
            ),
        )

        log.refresh_from_db()

        assert log.current_time == 2000
        assert is_player_episode(client, episode)


class TestClosePlayer:
    url = reverse_lazy("episodes:close_player")

    def test_player_empty(self, client, auth_user):
        response = client.post(
            self.url,
            HTTP_HX_TARGET="audio-player",
            HTTP_HX_REQUEST="true",
        )
        assert_ok(response)

    def test_close(
        self,
        client,
        auth_user,
        player_episode,
    ):

        log = create_audio_log(
            user=auth_user,
            current_time=2000,
            episode=player_episode,
        )

        response = client.post(
            self.url,
            HTTP_HX_TARGET="player",
            HTTP_HX_REQUEST="true",
        )
        assert_ok(response)

        log.refresh_from_db()

        assert log.current_time == 2000
        assert not is_player_episode(client, log.episode)


class TestPlayerTimeUpdate:
    url = reverse_lazy("episodes:player_time_update")

    @pytest.fixture
    def log(self, auth_user, player_episode):
        return create_audio_log(user=auth_user, episode=player_episode)

    def test_is_running(self, client, auth_user, log):

        response = client.post(
            self.url,
            {"current_time": "1030"},
        )
        assert_no_content(response)

        log.refresh_from_db()

        assert log.current_time == 1030

    def test_player_not_running(self, client, auth_user, episode):

        response = client.post(
            self.url,
            {"current_time": "1030"},
        )
        assert_no_content(response)

    def test_missing_data(self, client, auth_user, player_episode):

        response = client.post(self.url)
        assert_bad_request(response)

    def test_invalid_data(self, client, auth_user, player_episode):

        response = client.post(self.url, {"current_time": "xyz"})
        assert_bad_request(response)


class TestBookmarks:
    url = reverse_lazy("episodes:bookmarks")

    def test_get(self, client, auth_user):
        create_batch(create_bookmark, 33, user=auth_user)

        response = client.get(self.url)

        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 30

    def test_ascending(self, client, auth_user):
        create_batch(create_bookmark, 33, user=auth_user)

        response = client.get(self.url, {"order": "asc"})

        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 30

    def test_empty(self, client, auth_user):

        response = client.get(self.url)

        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 0

    def test_search(self, client, auth_user):

        podcast = create_podcast(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            create_bookmark(
                user=auth_user,
                episode=create_episode(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        create_bookmark(user=auth_user, episode=create_episode(title="testing"))

        response = client.get(self.url, {"query": "testing"})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1


class TestAddBookmark:
    def test_post(self, client, auth_user, episode):

        response = client.post(
            reverse("episodes:add_bookmark", args=[episode.id]),
            HTTP_HX_TARGET=episode.get_bookmark_target(),
            HTTP_HX_REQUEST="true",
        )

        assert_ok(response)
        assert Bookmark.objects.filter(user=auth_user, episode=episode).exists()

    def test_already_bookmark(self, transactional_db, client, auth_user, episode):
        create_bookmark(episode=episode, user=auth_user)
        response = client.post(
            reverse("episodes:add_bookmark", args=[episode.id]),
            HTTP_HX_TARGET=episode.get_bookmark_target(),
            HTTP_HX_REQUEST="true",
        )
        assert_conflict(response)
        assert Bookmark.objects.filter(user=auth_user, episode=episode).exists()


class TestRemoveBookmark:
    def test_post(self, client, auth_user, episode):
        create_bookmark(user=auth_user, episode=episode)
        response = client.post(
            reverse("episodes:remove_bookmark", args=[episode.id]),
            HTTP_HX_TARGET=episode.get_bookmark_target(),
            HTTP_HX_REQUEST="true",
        )
        assert_ok(response)
        assert not Bookmark.objects.filter(user=auth_user, episode=episode).exists()


class TestHistory:
    url = reverse_lazy("episodes:history")

    def test_get(self, client, auth_user):
        create_batch(create_audio_log, 33, user=auth_user)
        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 30

    def test_empty(self, client, auth_user):
        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 0

    def test_ascending(self, client, auth_user):
        create_batch(create_audio_log, 33, user=auth_user)

        response = client.get(self.url, {"order": "asc"})
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 30

    def test_search(self, client, auth_user):

        podcast = create_podcast(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            create_audio_log(
                user=auth_user,
                episode=create_episode(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        create_audio_log(user=auth_user, episode=create_episode(title="testing"))
        response = client.get(self.url, {"query": "testing"})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1


class TestRemoveAudioLog:
    def url(self, episode):
        return reverse("episodes:remove_audio_log", args=[episode.id])

    def test_ok(self, client, auth_user, episode):
        create_audio_log(user=auth_user, episode=episode)
        create_audio_log(user=auth_user)

        assert_ok(
            client.post(
                self.url(episode),
                HTTP_HX_TARGET=episode.get_history_target(),
                HTTP_HX_REQUEST="true",
            )
        )

        assert not AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=auth_user).count() == 1

    def test_is_playing(self, client, auth_user, player_episode):
        """Do not remove log if episode is currently playing"""
        log = create_audio_log(user=auth_user, episode=player_episode)

        assert_ok(
            client.post(
                self.url(log.episode),
                HTTP_HX_TARGET=player_episode.get_history_target(),
                HTTP_HX_REQUEST="true",
            ),
        )
        assert AudioLog.objects.filter(user=auth_user, episode=log.episode).exists()

    def test_none_remaining(self, client, auth_user, episode):
        log = create_audio_log(user=auth_user, episode=episode)

        assert_ok(
            client.post(
                self.url(log.episode),
                HTTP_HX_TARGET=episode.get_history_target(),
                HTTP_HX_REQUEST="true",
            ),
        )

        assert not AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=auth_user).count() == 0
