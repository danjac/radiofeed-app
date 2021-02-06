# Standard Library
import http
import json

# Django
from django.urls import reverse

# Third Party Libraries
import pytest

# RadioFeed
from radiofeed.podcasts.factories import PodcastFactory, SubscriptionFactory

# Local
from ..factories import AudioLogFactory, BookmarkFactory, EpisodeFactory
from ..models import AudioLog, Bookmark

pytestmark = pytest.mark.django_db


class TestEpisodeList:
    def test_user_no_subscriptions(self, client, login_user):
        EpisodeFactory.create_batch(3)
        resp = client.get(reverse("episodes:episode_list"))
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 0

    def test_user_has_subscriptions(self, client, login_user):
        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        SubscriptionFactory(user=login_user, podcast=episode.podcast)

        resp = client.get(reverse("episodes:episode_list"))
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == episode


class TestSearchEpisodes:
    def test_search_empty_anonymous(self, client):
        resp = client.get(reverse("episodes:search_episodes"), {"q": ""})
        assert resp.url == reverse("podcasts:podcast_list")

    def test_search_empty_authenticated(self, client, login_user):
        resp = client.get(reverse("episodes:search_episodes"), {"q": ""})
        assert resp.url == reverse("episodes:episode_list")

    def test_search(self, client):
        EpisodeFactory.create_batch(3, title="zzzz", keywords="zzzz")
        episode = EpisodeFactory(title="testing")
        resp = client.get(reverse("episodes:search_episodes"), {"q": "testing"})
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == episode


class TestEpisodeDetail:
    def test_anonymous(self, client, episode):
        resp = client.get(episode.get_absolute_url())
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_bookmarked"]

    def test_user_not_bookmarked(self, client, login_user, episode):
        resp = client.get(episode.get_absolute_url())
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_bookmarked"]

    def test_user_bookmarked(self, client, login_user, episode):
        BookmarkFactory(episode=episode, user=login_user)
        resp = client.get(episode.get_absolute_url())
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert resp.context_data["is_bookmarked"]


class TestEpisodeActions:
    def test_not_turbo_frame(self, client, login_user, episode):
        resp = client.get(
            reverse("episodes:actions", args=[episode.id]),
        )
        assert resp.url == episode.get_absolute_url()

    def test_user_not_bookmarked(self, client, login_user, episode):
        resp = client.get(
            reverse("episodes:actions", args=[episode.id]), HTTP_TURBO_FRAME="modal"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_bookmarked"]

    def test_user_bookmarked(self, client, login_user, episode):
        BookmarkFactory(episode=episode, user=login_user)
        resp = client.get(
            reverse("episodes:actions", args=[episode.id]), HTTP_TURBO_FRAME="modal"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert resp.context_data["is_bookmarked"]


class TestTogglePlayer:
    def test_play(self, client, login_user, episode):
        resp = client.post(reverse("episodes:start_player", args=[episode.id]))
        assert resp.status_code == http.HTTPStatus.OK

        header = json.loads(resp["X-Player"])
        assert header["action"] == "start"
        assert header["currentTime"] == 0
        assert header["mediaUrl"] == episode.media_url

        assert client.session["player"] == {
            "episode": episode.id,
            "current_time": 0,
            "playback_rate": 1.0,
        }

    def test_is_played(self, client, login_user, episode):
        AudioLogFactory(user=login_user, episode=episode, current_time=2000)
        resp = client.post(reverse("episodes:start_player", args=[episode.id]))
        assert resp.status_code == http.HTTPStatus.OK

        header = json.loads(resp["X-Player"])
        assert header["action"] == "start"
        assert header["currentTime"] == 2000
        assert header["mediaUrl"] == episode.media_url

        assert client.session["player"] == {
            "episode": episode.id,
            "current_time": 2000,
            "playback_rate": 1.0,
        }

    def test_stop(self, client, login_user, episode):
        session = client.session
        session.update({"player": {"episode": episode.id, "current_time": 1000}})
        session.save()

        AudioLogFactory(user=login_user, episode=episode, current_time=2000)
        resp = client.post(
            reverse("episodes:stop_player"),
            {"player_action": "stop"},
        )
        assert resp.status_code == http.HTTPStatus.OK

        header = json.loads(resp["X-Player"])
        assert header["action"] == "stop"


class TestPlayerTimeUpdate:
    def test_anonymous(self, client, anonymous_user, episode):
        resp = client.post(
            reverse("episodes:player_timeupdate"),
            data={"current_time": "1030.0001", "playback_rate": "1.2"},
        )
        assert resp.status_code == http.HTTPStatus.FORBIDDEN

    def test_authenticated(self, client, login_user, episode):
        session = client.session
        session.update(
            {
                "player": {
                    "episode": episode.id,
                    "current_time": 1000,
                    "playback_rate": 1.0,
                }
            }
        )
        session.save()

        resp = client.post(
            reverse("episodes:player_timeupdate"),
            data={"current_time": "1030.0001", "playback_rate": "1.2"},
        )
        assert resp.status_code == http.HTTPStatus.NO_CONTENT
        assert client.session["player"]["current_time"] == 1030
        assert client.session["player"]["playback_rate"] == 1.2

        log = AudioLog.objects.get(user=login_user, episode=episode)
        assert log.current_time == 1030

    def test_player_not_running(self, client, login_user, episode):
        resp = client.post(
            reverse("episodes:player_timeupdate"),
            data={"current_time": "1030.0001", "playback_rate": "1.2"},
        )
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        assert AudioLog.objects.count() == 0

    def test_missing_data(self, client, login_user, episode):
        resp = client.post(
            reverse("episodes:player_timeupdate"),
        )

        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        assert AudioLog.objects.count() == 0

    def test_invalid_data(self, client, login_user, episode):
        resp = client.post(
            reverse("episodes:player_timeupdate"),
            data={"current_time": "xyz"},
        )

        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        assert AudioLog.objects.count() == 0


class TestHistory:
    def test_get(self, client, login_user):
        AudioLogFactory.create_batch(3, user=login_user)
        resp = client.get(reverse("episodes:history"))
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self, client, login_user):

        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            AudioLogFactory(
                user=login_user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        AudioLogFactory(user=login_user, episode=EpisodeFactory(title="testing"))
        resp = client.get(reverse("episodes:history"), {"q": "testing"})
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestBookmarkList:
    def test_get(self, client, login_user):
        BookmarkFactory.create_batch(3, user=login_user)
        resp = client.get(reverse("episodes:bookmark_list"))
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self, client, login_user):

        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            BookmarkFactory(
                user=login_user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        BookmarkFactory(user=login_user, episode=EpisodeFactory(title="testing"))
        resp = client.get(reverse("episodes:bookmark_list"), {"q": "testing"})
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestAddBookmark:
    def test_post(self, client, login_user, episode):
        resp = client.post(reverse("episodes:add_bookmark", args=[episode.id]))
        assert resp.url == episode.get_absolute_url()
        assert Bookmark.objects.filter(user=login_user, episode=episode).exists()


class TestRemoveBookmark:
    def test_post(self, client, login_user, episode):
        BookmarkFactory(user=login_user, episode=episode)
        resp = client.post(reverse("episodes:remove_bookmark", args=[episode.id]))
        assert resp.url == episode.get_absolute_url()
        assert not Bookmark.objects.filter(user=login_user, episode=episode).exists()


class TestRemoveHistory:
    def test_post(self, client, login_user, episode):
        AudioLogFactory(user=login_user, episode=episode)
        AudioLogFactory(user=login_user)
        resp = client.post(reverse("episodes:remove_history", args=[episode.id]))
        assert resp.url == reverse("episodes:history")
        assert not AudioLog.objects.filter(user=login_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=login_user).count() == 1
