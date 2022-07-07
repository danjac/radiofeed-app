from datetime import timedelta

import pytest

from django.urls import reverse, reverse_lazy

from radiofeed.episodes.factories import AudioLogFactory, BookmarkFactory, EpisodeFactory
from radiofeed.episodes.middleware import Player
from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.factories import PodcastFactory, SubscriptionFactory

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
    def test_anonymous_user(self, client, db, assert_ok):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)
        EpisodeFactory.create_batch(3)
        response = client.get(episodes_url)
        assert_ok(response)
        assert not response.context_data["has_subscriptions"]
        assert len(response.context_data["page_obj"].object_list) == 1

    def test_not_subscribed(self, client, db, auth_user, assert_ok):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)
        EpisodeFactory.create_batch(3)
        response = client.get(episodes_url)
        assert_ok(response)
        assert not response.context_data["has_subscriptions"]
        assert len(response.context_data["page_obj"].object_list) == 1

    def test_user_has_subscribed(self, client, auth_user, assert_ok):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        SubscriptionFactory(user=auth_user, podcast=episode.podcast)

        response = client.get(episodes_url)
        assert_ok(response)
        assert not response.context_data["promoted"]
        assert response.context_data["has_subscriptions"]
        assert len(response.context_data["page_obj"].object_list) == 1
        assert response.context_data["page_obj"].object_list[0] == episode

    def test_user_has_subscribed_promoted(self, client, auth_user, assert_ok):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        SubscriptionFactory(user=auth_user, podcast=episode.podcast)

        response = client.get(episodes_url, {"promoted": True})

        assert_ok(response)
        assert response.context_data["promoted"]
        assert response.context_data["has_subscriptions"]
        assert len(response.context_data["page_obj"].object_list) == 1
        assert response.context_data["page_obj"].object_list[0].podcast == promoted


class TestSearchEpisodes:
    url = reverse_lazy("episodes:search_episodes")

    def test_no_results(self, db, client, assert_ok):
        response = client.get(self.url, {"q": "test"})
        assert_ok(response)

    def test_search_empty(self, db, client):
        assert client.get(self.url, {"q": ""}).url == episodes_url

    def test_search(self, db, client, faker, assert_ok):
        EpisodeFactory.create_batch(3, title="zzzz", keywords="zzzz")
        episode = EpisodeFactory(title=faker.unique.name())
        response = client.get(
            self.url,
            {"q": episode.title},
        )
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 1
        assert response.context_data["page_obj"].object_list[0] == episode


class TestEpisodeDetail:
    @pytest.fixture
    def prev_episode(self, episode):
        return EpisodeFactory(podcast=episode.podcast, pub_date=episode.pub_date - timedelta(days=7))

    @pytest.fixture
    def next_episode(self, episode):
        return EpisodeFactory(podcast=episode.podcast, pub_date=episode.pub_date + timedelta(days=7))

    def test_anonymous(self, client, episode, prev_episode, next_episode, assert_ok):
        response = client.get(episode.get_absolute_url())
        assert_ok(response)
        assert response.context_data["episode"] == episode

    def test_authenticated(
        self,
        client,
        auth_user,
        episode,
        assert_ok,
        prev_episode,
        next_episode,
    ):
        response = client.get(episode.get_absolute_url())
        assert_ok(response)
        assert response.context_data["episode"] == episode


class TestStartPlayer:
    # we have a number of savepoints here adding to query count
    num_savepoints = 3

    def url(self, episode):
        return reverse("episodes:start_player", args=[episode.id])

    def test_play_from_start(self, client, db, auth_user, episode, assert_ok):
        assert_ok(client.post(self.url(episode)))

        assert AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert is_player_episode(client, episode)

    def test_another_episode_in_player(self, client, auth_user, episode, assert_ok):
        client.session[Player.session_key] = EpisodeFactory().id

        assert_ok(client.post(self.url(episode)))

        assert AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert is_player_episode(client, episode)

    def test_resume(self, client, auth_user, episode, assert_ok):
        log = AudioLogFactory(user=auth_user, episode=episode, current_time=2000)
        assert_ok(client.post(self.url(episode)))

        log.refresh_from_db()

        assert log.current_time == 2000
        assert is_player_episode(client, episode)


class TestClosePlayer:
    url = reverse_lazy("episodes:close_player")

    def test_player_empty(self, client, auth_user, assert_ok):
        response = client.post(self.url)
        assert_ok(response)

    def test_close(
        self,
        client,
        auth_user,
        player_episode,
        assert_ok,
    ):

        log = AudioLogFactory(
            user=auth_user,
            current_time=2000,
            episode=player_episode,
        )

        response = client.post(self.url)
        assert_ok(response)

        log.refresh_from_db()

        assert log.current_time == 2000
        assert not is_player_episode(client, log.episode)


class TestPlayerTimeUpdate:
    url = reverse_lazy("episodes:player_time_update")

    @pytest.fixture
    def log(self, auth_user, player_episode, assert_no_content):
        return AudioLogFactory(user=auth_user, episode=player_episode)

    def test_is_running(self, client, auth_user, log, assert_no_content):

        response = client.post(
            self.url,
            {"current_time": "1030"},
        )
        assert_no_content(response)

        log.refresh_from_db()

        assert log.current_time == 1030

    def test_player_not_running(self, client, auth_user, episode, assert_no_content):

        response = client.post(
            self.url,
            {"current_time": "1030"},
        )
        assert_no_content(response)

    def test_missing_data(self, client, auth_user, player_episode, assert_bad_request):

        response = client.post(self.url)
        assert_bad_request(response)

    def test_invalid_data(self, client, auth_user, player_episode, assert_bad_request):

        response = client.post(self.url, {"current_time": "xyz"})
        assert_bad_request(response)


class TestBookmarks:
    url = reverse_lazy("episodes:bookmarks")

    def test_get(self, client, auth_user, assert_ok):
        BookmarkFactory.create_batch(3, user=auth_user)

        response = client.get(self.url)

        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 3

    def test_search(self, client, auth_user, assert_ok):

        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            BookmarkFactory(
                user=auth_user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        BookmarkFactory(user=auth_user, episode=EpisodeFactory(title="testing"))

        response = client.get(self.url, {"q": "testing"})
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 1


class TestAddBookmark:
    def test_post(self, client, auth_user, episode, assert_ok):

        response = client.post(reverse("episodes:add_bookmark", args=[episode.id]))

        assert_ok(response)
        assert Bookmark.objects.filter(user=auth_user, episode=episode).exists()

    @pytest.mark.django_db(transaction=True)
    def test_already_bookmark(self, client, auth_user, episode, assert_conflict):
        BookmarkFactory(episode=episode, user=auth_user)
        response = client.post(reverse("episodes:add_bookmark", args=[episode.id]))
        assert_conflict(response)
        assert Bookmark.objects.filter(user=auth_user, episode=episode).exists()


class TestRemoveBookmark:
    def test_post(self, client, auth_user, episode, assert_ok):
        BookmarkFactory(user=auth_user, episode=episode)
        response = client.delete(reverse("episodes:remove_bookmark", args=[episode.id]))
        assert_ok(response)
        assert not Bookmark.objects.filter(user=auth_user, episode=episode).exists()


class TestHistory:
    url = reverse_lazy("episodes:history")

    def test_get(self, client, auth_user, assert_ok):
        AudioLogFactory.create_batch(3, user=auth_user)
        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 3

    def test_get_oldest_first(self, client, auth_user, assert_ok):
        AudioLogFactory.create_batch(3, user=auth_user)

        response = client.get(self.url, {"ordering": "asc"})
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 3

    def test_search(self, client, auth_user, assert_ok):

        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            AudioLogFactory(
                user=auth_user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        AudioLogFactory(user=auth_user, episode=EpisodeFactory(title="testing"))
        response = client.get(self.url, {"q": "testing"})
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 1


class TestRemoveAudioLog:
    def url(self, episode):
        return reverse("episodes:remove_audio_log", args=[episode.id])

    def test_ok(self, client, auth_user, episode, assert_ok):
        AudioLogFactory(user=auth_user, episode=episode)
        AudioLogFactory(user=auth_user)

        assert_ok(client.delete(self.url(episode)))

        assert not AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=auth_user).count() == 1

    def test_is_playing(self, client, auth_user, player_episode, assert_ok):
        """Do not remove log if episode is currently playing"""
        log = AudioLogFactory(user=auth_user, episode=player_episode)

        assert_ok(client.delete(self.url(log.episode)))
        assert AudioLog.objects.filter(user=auth_user, episode=log.episode).exists()

    def test_none_remaining(self, client, auth_user, episode, assert_ok):
        log = AudioLogFactory(user=auth_user, episode=episode)

        assert_ok(client.delete(self.url(log.episode)))

        assert not AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=auth_user).count() == 0
