import http

import pytest

from django.urls import reverse

from audiotrails.podcasts.factories import FollowFactory, PodcastFactory

from ..factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
    QueueItemFactory,
)
from ..models import AudioLog, Favorite, QueueItem

pytestmark = pytest.mark.django_db


class TestNewEpisodes:
    def test_anonymous(self, client, login_user):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)
        EpisodeFactory.create_batch(3)
        resp = client.get(reverse("episodes:index"), HTTP_TURBO_FRAME="episodes")
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["has_follows"]
        assert len(resp.context_data["page_obj"].object_list) == 1

    def test_user_no_subscriptions(self, client, login_user):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)
        resp = client.get(reverse("episodes:index"), HTTP_TURBO_FRAME="episodes")
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["has_follows"]
        assert len(resp.context_data["page_obj"].object_list) == 1

    def test_user_has_subscriptions(self, client, login_user):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        FollowFactory(user=login_user, podcast=episode.podcast)

        resp = client.get(reverse("episodes:index"), HTTP_TURBO_FRAME="episodes")
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["featured"]
        assert resp.context_data["has_follows"]
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == episode

    def test_user_has_subscriptions_featured(self, client, login_user):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        FollowFactory(user=login_user, podcast=episode.podcast)

        resp = client.get(reverse("episodes:featured"), HTTP_TURBO_FRAME="episodes")
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["featured"]
        assert resp.context_data["has_follows"]
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0].podcast == promoted


class TestSearchEpisodes:
    def test_page(self, client):
        resp = client.get(reverse("episodes:search_episodes"), {"q": "test"})
        assert resp.status_code == http.HTTPStatus.OK

    def test_search_empty_anonymous(self, client):
        resp = client.get(
            reverse("episodes:search_episodes"),
            {"q": ""},
        )
        assert resp.url == reverse("episodes:index")

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


class TestPreview:
    def test_not_turbo_frame(self, client, login_user, episode):
        resp = client.get(
            reverse("episodes:episode_preview", args=[episode.id]),
        )
        assert resp.url == episode.get_absolute_url()

    def test_user_not_favorited(self, client, login_user, episode):
        resp = client.get(
            reverse("episodes:episode_preview", args=[episode.id]),
            HTTP_TURBO_FRAME="modal",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_favorited"]

    def test_user_favorited(self, client, login_user, episode):
        FavoriteFactory(episode=episode, user=login_user)
        resp = client.get(
            reverse("episodes:episode_preview", args=[episode.id]),
            HTTP_TURBO_FRAME="modal",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert resp.context_data["is_favorited"]


class TestStartPlayer:
    def test_anonymous(self, client, episode):
        resp = client.post(reverse("episodes:start_player", args=[episode.id]))
        assert resp.url

    def test_play_from_start(self, client, login_user, episode):
        resp = client.post(reverse("episodes:start_player", args=[episode.id]))
        assert list(resp.streaming_content)
        assert resp.status_code == http.HTTPStatus.OK

    def test_play_episode_in_history(self, client, login_user, episode):
        AudioLogFactory(user=login_user, episode=episode, current_time=2000)
        resp = client.post(reverse("episodes:start_player", args=[episode.id]))
        assert list(resp.streaming_content)
        assert resp.status_code == http.HTTPStatus.OK


class TestPlayNextEpisode:
    def test_has_next_in_queue(self, client, login_user, episode):
        QueueItem.objects.create(position=0, user=login_user, episode=episode)
        resp = client.post(reverse("episodes:play_next_episode"))
        assert list(resp.streaming_content)
        assert resp.status_code == http.HTTPStatus.OK
        assert QueueItem.objects.count() == 0

    def test_play_next_episode_in_history(self, client, login_user):
        log = AudioLogFactory(user=login_user, current_time=30)

        QueueItem.objects.create(position=0, user=login_user, episode=log.episode)
        resp = client.post(reverse("episodes:play_next_episode"))
        assert list(resp.streaming_content)
        assert resp.status_code == http.HTTPStatus.OK
        assert QueueItem.objects.count() == 0

    def test_queue_empty(self, client, login_user):
        resp = client.post(reverse("episodes:play_next_episode"))
        assert list(resp.streaming_content)
        assert resp.status_code == http.HTTPStatus.OK


class TestClosePlayer:
    def test_anonymous(self, client):
        resp = client.post(
            reverse("episodes:close_player"),
        )
        assert resp.url

    def test_stop(self, client, login_user, episode):
        session = client.session
        session.update({"player": {"episode": episode.id, "current_time": 1000}})
        session.save()

        AudioLogFactory(user=login_user, episode=episode, current_time=2000)
        resp = client.post(
            reverse("episodes:close_player"),
        )
        assert list(resp.streaming_content)
        assert resp.status_code == http.HTTPStatus.OK


class TestPlayerUpdateCurrentTime:
    def test_anonymous(self, client, anonymous_user, episode):
        resp = client.post(
            reverse("episodes:player_update_current_time"),
            data={"current_time": "1030.0001"},
        )
        assert resp.status_code == http.HTTPStatus.FORBIDDEN

    def test_authenticated(self, client, login_user, episode):
        log = AudioLogFactory(user=login_user, episode=episode)

        session = client.session
        session["player_episode"] = episode.id
        session.save()

        resp = client.post(
            reverse("episodes:player_update_current_time"),
            data={"current_time": "1030.0001"},
        )
        assert resp.status_code == http.HTTPStatus.NO_CONTENT

        log.refresh_from_db()
        assert log.current_time == 1030

    def test_player_not_running(self, client, login_user, episode):
        resp = client.post(
            reverse("episodes:player_update_current_time"),
            data={"current_time": "1030.0001"},
        )
        assert resp.status_code == http.HTTPStatus.NO_CONTENT
        assert AudioLog.objects.count() == 0

    def test_missing_data(self, client, login_user, episode):
        session = client.session
        session["player_episode"] = episode.id
        session.save()

        resp = client.post(
            reverse("episodes:player_update_current_time"),
        )

        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        assert AudioLog.objects.count() == 0

    def test_invalid_data(self, client, login_user, episode):
        session = client.session
        session["player_episode"] = episode.id
        session.save()

        resp = client.post(
            reverse("episodes:player_update_current_time"),
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


class TestFavorites:
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
    def test_anonymous(self, client, episode):
        resp = client.post(reverse("episodes:add_favorite", args=[episode.id]))
        assert resp.url

    def test_post(self, client, login_user, episode):
        resp = client.post(reverse("episodes:add_favorite", args=[episode.id]))
        assert resp.status_code == http.HTTPStatus.OK
        assert Favorite.objects.filter(user=login_user, episode=episode).exists()

    @pytest.mark.django_db(transaction=True)
    def test_already_favorite(self, client, login_user, episode):
        FavoriteFactory(episode=episode, user=login_user)
        resp = client.post(reverse("episodes:add_favorite", args=[episode.id]))
        assert resp.status_code == http.HTTPStatus.OK


class TestRemoveFavorite:
    def test_anonymous(self, client, episode):
        resp = client.post(reverse("episodes:remove_favorite", args=[episode.id]))
        assert resp.url

    def test_post(self, client, login_user, episode):
        FavoriteFactory(user=login_user, episode=episode)
        resp = client.post(reverse("episodes:remove_favorite", args=[episode.id]))
        assert resp.status_code == http.HTTPStatus.OK
        assert not Favorite.objects.filter(user=login_user, episode=episode).exists()


class TestRemoveHistory:
    def test_anonymous(self, client, episode):
        resp = client.post(reverse("episodes:remove_audio_log", args=[episode.id]))
        assert resp.url

    def test_post(self, client, login_user, episode):
        AudioLogFactory(user=login_user, episode=episode)
        AudioLogFactory(user=login_user)
        resp = client.post(reverse("episodes:remove_audio_log", args=[episode.id]))
        assert resp.status_code == http.HTTPStatus.OK
        assert not AudioLog.objects.filter(user=login_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=login_user).count() == 1

    def test_post_none_remaining(self, client, login_user, episode):
        AudioLogFactory(user=login_user, episode=episode)
        resp = client.post(reverse("episodes:remove_audio_log", args=[episode.id]))
        assert resp.status_code == http.HTTPStatus.OK
        assert not AudioLog.objects.filter(user=login_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=login_user).count() == 0


class TestQueue:
    def test_get(self, client, login_user):
        QueueItemFactory.create_batch(3, user=login_user)
        resp = client.get(reverse("episodes:queue"))
        assert resp.status_code == http.HTTPStatus.OK


class TestAddToQueue:
    def test_anonymous(self, client, episode):
        resp = client.post(reverse("episodes:add_to_queue", args=[episode.id]))
        assert resp.url

    def test_post(self, client, login_user):
        first = EpisodeFactory()
        second = EpisodeFactory()
        third = EpisodeFactory()

        for episode in (first, second, third):
            resp = client.post(
                reverse(
                    "episodes:add_to_queue",
                    args=[episode.id],
                ),
            )
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

    @pytest.mark.django_db(transaction=True)
    def test_post_already_queued(self, client, login_user, episode):
        QueueItemFactory(episode=episode, user=login_user)
        resp = client.post(
            reverse(
                "episodes:add_to_queue",
                args=[episode.id],
            ),
        )
        assert resp.status_code == http.HTTPStatus.OK


class TestRemoveFromQueue:
    def test_anonymous(self, client, episode):
        resp = client.post(reverse("episodes:remove_from_queue", args=[episode.id]))
        assert resp.url

    def test_post(self, client, login_user):
        item = QueueItemFactory(user=login_user)
        resp = client.post(
            reverse("episodes:remove_from_queue", args=[item.episode.id])
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert QueueItem.objects.filter(user=login_user).count() == 0


class TestMoveQueueItems:
    def test_anonymous(self, client, episode):
        resp = client.post(reverse("episodes:move_queue_items"))
        assert resp.status_code == http.HTTPStatus.FORBIDDEN

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
