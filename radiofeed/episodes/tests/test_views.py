import http
import json

from django.urls import reverse

import pytest

from radiofeed.podcasts.factories import PodcastFactory, SubscriptionFactory

from ..factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
    QueueItemFactory,
)
from ..models import AudioLog, Favorite, QueueItem

pytestmark = pytest.mark.django_db


class TestNewEpisodes:
    def test_user_no_subscriptions(self, client, login_user):
        EpisodeFactory.create_batch(3)
        resp = client.get(reverse("episodes:index"), HTTP_TURBO_FRAME="episodes")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 0

    def test_user_has_subscriptions(self, client, login_user):
        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        SubscriptionFactory(user=login_user, podcast=episode.podcast)

        resp = client.get(reverse("episodes:index"), HTTP_TURBO_FRAME="episodes")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == episode


class TestSearchEpisodes:
    def test_page(self, client):
        resp = client.get(reverse("episodes:search_episodes"), {"q": "test"})
        assert resp.status_code == http.HTTPStatus.OK

    def test_search_empty_anonymous(self, client):
        resp = client.get(
            reverse("episodes:search_episodes"),
            {"q": ""},
        )
        assert resp.url == reverse("podcasts:index")

    def test_search_empty_authenticated(self, client, login_user):
        resp = client.get(
            reverse("episodes:search_episodes"),
            {"q": ""},
        )
        assert resp.url == reverse("episodes:index")

    def test_search(self, client):
        EpisodeFactory.create_batch(3, title="zzzz", keywords="zzzz")
        episode = EpisodeFactory(title="testing")
        resp = client.get(
            reverse("episodes:search_episodes"),
            {"q": "testing"},
            HTTP_TURBO_FRAME="episodes",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == episode


class TestEpisodeDetail:
    def test_anonymous(self, client, episode):
        resp = client.get(episode.get_absolute_url())
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_favorited"]

    def test_user_not_favorited(self, client, login_user, episode):
        resp = client.get(episode.get_absolute_url())
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_favorited"]

    def test_user_favorited(self, client, login_user, episode):
        FavoriteFactory(episode=episode, user=login_user)
        resp = client.get(episode.get_absolute_url())
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert resp.context_data["is_favorited"]


class TestEpisodeActions:
    def test_not_turbo_frame(self, client, login_user, episode):
        resp = client.get(
            reverse("episodes:actions", args=[episode.id]),
        )
        assert resp.url == episode.get_absolute_url()

    def test_user_not_favorited(self, client, login_user, episode):
        resp = client.get(
            reverse("episodes:actions", args=[episode.id]), HTTP_TURBO_FRAME="modal"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_favorited"]

    def test_user_favorited(self, client, login_user, episode):
        FavoriteFactory(episode=episode, user=login_user)
        resp = client.get(
            reverse("episodes:actions", args=[episode.id]), HTTP_TURBO_FRAME="modal"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert resp.context_data["is_favorited"]


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

    def test_play_next(self, client, login_user, episode):
        QueueItem.objects.create(position=0, user=login_user, episode=episode)
        resp = client.post(reverse("episodes:play_next_episode"))
        assert resp.status_code == http.HTTPStatus.OK

        assert QueueItem.objects.count() == 0

        header = json.loads(resp["X-Player"])
        assert header["action"] == "start"
        assert header["currentTime"] == 0
        assert header["mediaUrl"] == episode.media_url

        assert client.session["player"] == {
            "episode": episode.id,
            "current_time": 0,
            "playback_rate": 1.0,
        }

    def test_play_next_if_empty(self, client, login_user):
        resp = client.post(reverse("episodes:play_next_episode"))
        assert resp.status_code == http.HTTPStatus.OK

        header = json.loads(resp["X-Player"])
        assert header["action"] == "stop"

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
        resp = client.get(reverse("episodes:history"), HTTP_TURBO_FRAME="episodes")
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
        resp = client.get(
            reverse("episodes:history"), {"q": "testing"}, HTTP_TURBO_FRAME="episodes"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestFavoriteList:
    def test_get(self, client, login_user):
        FavoriteFactory.create_batch(3, user=login_user)
        resp = client.get(reverse("episodes:favorites"), HTTP_TURBO_FRAME="episodes")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self, client, login_user):

        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            FavoriteFactory(
                user=login_user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        FavoriteFactory(user=login_user, episode=EpisodeFactory(title="testing"))
        resp = client.get(
            reverse("episodes:favorites"),
            {"q": "testing"},
            HTTP_TURBO_FRAME="episodes",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestAddFavorite:
    def test_post(self, client, login_user, episode):
        resp = client.post(reverse("episodes:add_favorite", args=[episode.id]))
        assert resp.status_code == http.HTTPStatus.OK
        assert Favorite.objects.filter(user=login_user, episode=episode).exists()


class TestRemoveFavorite:
    def test_post(self, client, login_user, episode):
        FavoriteFactory(user=login_user, episode=episode)
        resp = client.post(reverse("episodes:remove_favorite", args=[episode.id]))
        assert resp.status_code == http.HTTPStatus.OK
        assert not Favorite.objects.filter(user=login_user, episode=episode).exists()


class TestRemoveHistory:
    def test_post(self, client, login_user, episode):
        AudioLogFactory(user=login_user, episode=episode)
        AudioLogFactory(user=login_user)
        resp = client.post(reverse("episodes:remove_history", args=[episode.id]))
        assert resp.url == reverse("episodes:history")
        assert not AudioLog.objects.filter(user=login_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=login_user).count() == 1


class TestAddToQueue:
    def test_post(self, client, login_user):
        first = EpisodeFactory()
        second = EpisodeFactory()
        third = EpisodeFactory()

        for episode in (first, second, third):
            resp = client.post(reverse("episodes:add_to_queue", args=[episode.id]))
            assert resp.status_code == http.HTTPStatus.OK

        items = (
            QueueItem.objects.filter(user=login_user)
            .select_related("episode")
            .order_by("position")
        )

        assert items[0].episode == first
        assert items[0].position == 1

        assert items[1].episode == second
        assert items[1].position == 2

        assert items[2].episode == third
        assert items[2].position == 3


class TestRemoveFromQueue:
    def test_post(self, client, login_user):
        item = QueueItemFactory(user=login_user)
        resp = client.post(
            reverse("episodes:remove_from_queue", args=[item.episode.id])
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert QueueItem.objects.filter(user=login_user).count() == 0


class TestMoveQueueItems:
    def test_post(self, client, login_user):

        first = QueueItemFactory(user=login_user)
        second = QueueItemFactory(user=login_user)
        third = QueueItemFactory(user=login_user)

        items = QueueItem.objects.filter(user=login_user).order_by("position")

        assert items[0] == first
        assert items[1] == second
        assert items[2] == third

        resp = client.post(
            reverse("episodes:move_queue_items"),
            {
                "items": [
                    third.id,
                    first.id,
                    second.id,
                ]
            },
        )

        assert resp.status_code == http.HTTPStatus.NO_CONTENT

        items = QueueItem.objects.filter(user=login_user).order_by("position")

        assert items[0] == third
        assert items[1] == first
        assert items[2] == second
