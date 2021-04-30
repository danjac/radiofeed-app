import http

from django.test import TestCase, TransactionTestCase
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


class PlayerUpdateCurrentTimeAnonymousTests(TestCase):
    def test_post(self):
        EpisodeFactory()
        resp = self.client.post(
            reverse("episodes:player_update_current_time"),
            data={"current_time": "1030.0001"},
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.FORBIDDEN)


class PlayerUpdateCurrentTimeAuthenticatedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_is_running(self):
        log = AudioLogFactory(user=self.user, episode=self.episode)

        session = self.client.session
        session["player_episode"] = self.episode.id
        session.save()

        resp = self.client.post(
            reverse("episodes:player_update_current_time"),
            data={"current_time": "1030.0001"},
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)

        log.refresh_from_db()
        self.assertEqual(log.current_time, 1030)

    def test_player_not_running(self):
        resp = self.client.post(
            reverse("episodes:player_update_current_time"),
            data={"current_time": "1030.0001"},
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)

    def test_missing_data(self):
        session = self.client.session
        session["player_episode"] = self.episode.id
        session.save()

        resp = self.client.post(
            reverse("episodes:player_update_current_time"),
        )

        self.assertEqual(resp.status_code, http.HTTPStatus.BAD_REQUEST)

    def test_invalid_data(self):
        session = self.client.session
        session["player_episode"] = self.episode.id
        session.save()

        resp = self.client.post(
            reverse("episodes:player_update_current_time"),
            data={"current_time": "xyz"},
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.BAD_REQUEST)


class HistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_get(self):
        AudioLogFactory.create_batch(3, user=self.user)
        resp = self.client.get(reverse("episodes:history"), HTTP_TURBO_FRAME="episodes")
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 3)

    def test_search(self):

        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            AudioLogFactory(
                user=self.user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        AudioLogFactory(user=self.user, episode=EpisodeFactory(title="testing"))
        resp = self.client.get(
            reverse("episodes:history"), {"q": "testing"}, HTTP_TURBO_FRAME="episodes"
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)


class FavoritesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_get(self):
        FavoriteFactory.create_batch(3, user=self.user)
        resp = self.client.get(
            reverse("episodes:favorites"), HTTP_TURBO_FRAME="episodes"
        )

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 3)

    def test_search(self):

        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            FavoriteFactory(
                user=self.user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        FavoriteFactory(user=self.user, episode=EpisodeFactory(title="testing"))
        resp = self.client.get(
            reverse("episodes:favorites"),
            {"q": "testing"},
            HTTP_TURBO_FRAME="episodes",
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)


class AddFavoriteAnonymousTests(TestCase):
    def test_anonymous(self):
        episode = EpisodeFactory()
        self.assertRedirects(
            self.client.post(reverse("episodes:add_favorite", args=[episode.id])),
            f"{reverse('account_login')}?next={episode.get_absolute_url()}",
        )


class AddFavoriteAuthenticatedTests(TransactionTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.episode = EpisodeFactory()
        self.client.force_login(self.user)

    def test_post(self):
        resp = self.client.post(
            reverse("episodes:add_favorite", args=[self.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertTrue(
            Favorite.objects.filter(user=self.user, episode=self.episode).exists()
        )

    def test_already_favorite(self):
        FavoriteFactory(episode=self.episode, user=self.user)
        resp = self.client.post(
            reverse("episodes:add_favorite", args=[self.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertTrue(
            Favorite.objects.filter(user=self.user, episode=self.episode).exists()
        )


class RemoveFavoriteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.episode = EpisodeFactory()

    def test_anonymous(self):
        self.assertRedirects(
            self.client.post(
                reverse("episodes:remove_favorite", args=[self.episode.id])
            ),
            f"{reverse('account_login')}?next={self.episode.get_absolute_url()}",
        )

    def test_post(self):
        user = UserFactory()
        self.client.force_login(user)
        FavoriteFactory(user=user, episode=self.episode)
        resp = self.client.post(
            reverse("episodes:remove_favorite", args=[self.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(
            Favorite.objects.filter(user=user, episode=self.episode).exists()
        )


class RemoveAudioLogAnonymousTests(TestCase):
    def test_anonymous(self):
        episode = EpisodeFactory()
        self.assertRedirects(
            self.client.post(reverse("episodes:remove_audio_log", args=[episode.id])),
            f"{reverse('account_login')}?next={episode.get_absolute_url()}",
        )


class RemoveAudioLogAuthenticatedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_post(self):
        AudioLogFactory(user=self.user, episode=self.episode)
        AudioLogFactory(user=self.user)
        resp = self.client.post(
            reverse("episodes:remove_audio_log", args=[self.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(
            AudioLog.objects.filter(user=self.user, episode=self.episode).exists()
        )
        self.assertEqual(AudioLog.objects.filter(user=self.user).count(), 1)

    def test_post_none_remaining(self):
        AudioLogFactory(user=self.user, episode=self.episode)
        resp = self.client.post(
            reverse("episodes:remove_audio_log", args=[self.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(
            AudioLog.objects.filter(user=self.user, episode=self.episode).exists()
        )
        self.assertEqual(AudioLog.objects.filter(user=self.user).count(), 0)


class QueueTests(TestCase):
    def test_get(self):
        user = UserFactory()
        self.client.force_login(user)

        QueueItemFactory.create_batch(3, user=user)
        resp = self.client.get(reverse("episodes:queue"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)


class AddToQueueAnonymousTests(TestCase):
    def test_post(self):
        episode = EpisodeFactory()
        self.assertRedirects(
            self.client.post(reverse("episodes:add_to_queue", args=[episode.id])),
            f"{reverse('account_login')}?next={episode.get_absolute_url()}",
        )


class AddToQueueAuthenticatedTests(TransactionTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.episode = EpisodeFactory()
        self.client.force_login(self.user)

    def test_post(self):
        first = EpisodeFactory()
        second = EpisodeFactory()
        third = EpisodeFactory()

        for episode in (first, second, third):
            resp = self.client.post(
                reverse(
                    "episodes:add_to_queue",
                    args=[episode.id],
                ),
            )
            self.assertEqual(resp.status_code, http.HTTPStatus.OK)

        items = (
            QueueItem.objects.filter(user=self.user)
            .select_related("episode")
            .order_by("position")
        )

        self.assertEqual(items[0].episode, first)
        self.assertEqual(items[0].position, 1)

        self.assertEqual(items[1].episode, second)
        self.assertEqual(items[1].position, 2)

        self.assertEqual(items[2].episode, third)
        self.assertEqual(items[2].position, 3)

    def test_post_already_queued(self):
        QueueItemFactory(episode=self.episode, user=self.user)
        resp = self.client.post(
            reverse(
                "episodes:add_to_queue",
                args=[self.episode.id],
            ),
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)


class RemoveFromQueueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.episode = EpisodeFactory()

    def test_anonymous(self):
        self.assertRedirects(
            self.client.post(
                reverse("episodes:remove_from_queue", args=[self.episode.id])
            ),
            f"{reverse('account_login')}?next={self.episode.get_absolute_url()}",
        )

    def test_post(self):
        user = UserFactory()
        self.client.force_login(user)
        item = QueueItemFactory(user=user)
        resp = self.client.post(
            reverse("episodes:remove_from_queue", args=[item.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(QueueItem.objects.filter(user=user).count(), 0)


class TestMoveQueueItems:
    def test_anonymous(self):
        resp = self.client.post(reverse("episodes:move_queue_items"))
        self.assertEqual(resp.status_code, http.HTTPStatus.FORBIDDEN)

    def test_post(self):
        user = UserFactory()
        self.client.force_login(user)

        first = QueueItemFactory(user=user)
        second = QueueItemFactory(user=user)
        third = QueueItemFactory(user=user)

        items = QueueItem.objects.filter(user=user).order_by("position")

        self.assertEqual(items[0], first)
        self.assertEqual(items[1], second)
        self.assertEqual(items[2], third)

        resp = self.client.post(
            reverse("episodes:move_queue_items"),
            {
                "items": [
                    third.id,
                    first.id,
                    second.id,
                ]
            },
        )

        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)

        items = QueueItem.objects.filter(user=user).order_by("position")

        self.assertEqual(items[0], third)
        self.assertEqual(items[1], first)
        self.assertEqual(items[2], second)
