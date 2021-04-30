import http

from django.test import TestCase
from django.urls import reverse

from audiotrails.podcasts.factories import FollowFactory, PodcastFactory
from audiotrails.users.factories import UserFactory

from ..factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
    QueueItemFactory,
)
from ..models import AudioLog, Favorite, QueueItem


class NewEpisodesAnonymousTests(TestCase):
    def test_get(self):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)
        EpisodeFactory.create_batch(3)
        resp = self.client.get(reverse("episodes:index"), HTTP_TURBO_FRAME="episodes")
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(resp.context_data["has_follows"])
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)


class NewEpisodesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_user_no_subscriptions(self):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)
        resp = self.client.get(reverse("episodes:index"), HTTP_TURBO_FRAME="episodes")
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(resp.context_data["has_follows"])
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)

    def test_user_has_subscriptions(self):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        FollowFactory(user=self.user, podcast=episode.podcast)

        resp = self.client.get(reverse("episodes:index"), HTTP_TURBO_FRAME="episodes")
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(resp.context_data["featured"])
        self.assertTrue(resp.context_data["has_follows"])
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)
        self.assertEqual(resp.context_data["page_obj"].object_list[0], episode)

    def test_user_has_subscriptions_featured(self):
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        FollowFactory(user=self.user, podcast=episode.podcast)

        resp = self.client.get(
            reverse("episodes:featured"), HTTP_TURBO_FRAME="episodes"
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertTrue(resp.context_data["featured"])
        self.assertTrue(resp.context_data["has_follows"])
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)
        self.assertEqual(resp.context_data["page_obj"].object_list[0].podcast, promoted)


class SearchEpisodesTests(TestCase):
    def test_page(self):
        resp = self.client.get(reverse("episodes:search_episodes"), {"q": "test"})
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)

    def test_search_empty(self):
        self.assertRedirects(
            self.client.get(reverse("episodes:search_episodes"), {"q": ""}),
            reverse("episodes:index"),
        )

    def test_search(self):
        EpisodeFactory.create_batch(3, title="zzzz", keywords="zzzz")
        episode = EpisodeFactory(title="testing")
        resp = self.client.get(
            reverse("episodes:search_episodes"),
            {"q": "testing"},
            HTTP_TURBO_FRAME="episodes",
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)
        self.assertEqual(resp.context_data["page_obj"].object_list[0], episode)


class EpisodeDetailAnonymousTests(TestCase):
    def test_get(self):
        episode = EpisodeFactory()
        resp = self.client.get(episode.get_absolute_url())
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context_data["episode"], episode)
        self.assertFalse(resp.context_data["is_favorited"])


class EpisodeDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_user_not_favorited(self):
        resp = self.client.get(self.episode.get_absolute_url())
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context_data["episode"], self.episode)
        self.assertFalse(resp.context_data["is_favorited"])

    def test_user_favorited(self):
        FavoriteFactory(episode=self.episode, user=self.user)
        resp = self.client.get(self.episode.get_absolute_url())
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context_data["episode"], self.episode)
        self.assertTrue(resp.context_data["is_favorited"])


class PreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_not_turbo_frame(self):
        self.assertRedirects(
            self.client.get(
                reverse("episodes:episode_preview", args=[self.episode.id]),
            ),
            self.episode.get_absolute_url(),
        )

    def test_user_not_favorited(self):
        resp = self.client.get(
            reverse("episodes:episode_preview", args=[self.episode.id]),
            HTTP_TURBO_FRAME="modal",
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context_data["episode"], self.episode)
        self.assertFalse(resp.context_data["is_favorited"])

    def test_user_favorited(self):
        FavoriteFactory(episode=self.episode, user=self.user)
        resp = self.client.get(
            reverse("episodes:episode_preview", args=[self.episode.id]),
            HTTP_TURBO_FRAME="modal",
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context_data["episode"], self.episode)
        self.assertTrue(resp.context_data["is_favorited"])


class StartPlayerAnonymousTests(TestCase):
    def test_get(self):
        episode = EpisodeFactory()
        self.assertRedirects(
            self.client.post(reverse("episodes:start_player", args=[episode.id])),
            f"{reverse('account_login')}?next={episode.get_absolute_url()}",
        )


class StartPlayerAuthenticatedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_play_from_start(self):
        resp = self.client.post(
            reverse("episodes:start_player", args=[self.episode.id])
        )

        list(resp.streaming_content)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)

    def test_play_episode_in_history(self):
        AudioLogFactory(user=self.user, episode=self.episode, current_time=2000)
        resp = self.client.post(
            reverse("episodes:start_player", args=[self.episode.id])
        )
        list(resp.streaming_content)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)


class PlayNextEpisodeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_has_next_in_queue(self):
        QueueItem.objects.create(position=0, user=self.user, episode=self.episode)
        resp = self.client.post(reverse("episodes:play_next_episode"))

        list(resp.streaming_content)

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(QueueItem.objects.count(), 0)

    def test_play_next_episode_in_history(self):
        log = AudioLogFactory(user=self.user, current_time=30)

        QueueItem.objects.create(position=0, user=self.user, episode=log.episode)
        resp = self.client.post(reverse("episodes:play_next_episode"))

        list(resp.streaming_content)

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(QueueItem.objects.count(), 0)

    def test_queue_empty(self):
        resp = self.client.post(reverse("episodes:play_next_episode"))

        list(resp.streaming_content)

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(QueueItem.objects.count(), 0)


class ClosePlayerTests(TestCase):
    def test_anonymous(self):
        self.assertRedirects(
            self.client.post(
                reverse("episodes:close_player"),
            ),
            reverse("account_login") + "?next=/",
        )

    def test_stop(self):
        episode = EpisodeFactory()

        user = UserFactory()
        self.client.force_login(user)

        session = self.client.session
        session.update({"player": {"episode": episode.id, "current_time": 1000}})
        session.save()

        AudioLogFactory(user=user, episode=episode, current_time=2000)
        resp = self.client.post(
            reverse("episodes:close_player"),
        )
        list(resp.streaming_content)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)


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
