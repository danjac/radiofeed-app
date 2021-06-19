import http

from django.test import TestCase, TransactionTestCase
from django.urls import reverse, reverse_lazy

from audiotrails.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
    QueueItemFactory,
)
from audiotrails.episodes.models import AudioLog, Favorite, QueueItem
from audiotrails.podcasts.factories import FollowFactory, PodcastFactory
from audiotrails.users.factories import UserFactory

episodes_url = reverse_lazy("episodes:index")


class NewEpisodesAnonymousTests(TestCase):
    def test_get(self) -> None:
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)
        EpisodeFactory.create_batch(3)
        resp = self.client.get(episodes_url)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(resp.context_data["has_follows"])
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)


class NewEpisodesAuthenticatedTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_user_no_subscriptions(self) -> None:
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)
        resp = self.client.get(episodes_url)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(resp.context_data["has_follows"])
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)

    def test_user_has_subscriptions(self) -> None:
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        FollowFactory(user=self.user, podcast=episode.podcast)

        resp = self.client.get(episodes_url)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(resp.context_data["featured"])
        self.assertTrue(resp.context_data["has_follows"])
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)
        self.assertEqual(resp.context_data["page_obj"].object_list[0], episode)

    def test_user_has_listened_items(self) -> None:
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)

        log = AudioLogFactory(user=self.user)
        FollowFactory(user=self.user, podcast=log.episode.podcast)

        episode = EpisodeFactory()
        FollowFactory(user=self.user, podcast=episode.podcast)

        resp = self.client.get(episodes_url)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(resp.context_data["featured"])
        self.assertTrue(resp.context_data["has_follows"])
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)
        self.assertEqual(resp.context_data["page_obj"].object_list[0], episode)

        episode_ids = [obj.id for obj in resp.context_data["page_obj"].object_list]
        self.assertNotIn(log.episode.id, episode_ids)

    def test_user_has_subscriptions_featured(self) -> None:
        promoted = PodcastFactory(promoted=True)
        EpisodeFactory(podcast=promoted)

        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        FollowFactory(user=self.user, podcast=episode.podcast)

        resp = self.client.get(reverse("episodes:featured"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertTrue(resp.context_data["featured"])
        self.assertTrue(resp.context_data["has_follows"])
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)
        self.assertEqual(resp.context_data["page_obj"].object_list[0].podcast, promoted)


class SearchEpisodesTests(TransactionTestCase):
    def setUp(self):
        self.url = reverse("episodes:search_episodes")

    def test_page(self) -> None:
        resp = self.client.get(self.url, {"q": "test"})
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)

    def test_search_empty(self) -> None:
        self.assertRedirects(
            self.client.get(self.url, {"q": ""}),
            reverse("episodes:index"),
        )

    def test_search(self) -> None:
        EpisodeFactory.create_batch(3, title="zzzz", keywords="zzzz")
        episode = EpisodeFactory(title="testing")
        resp = self.client.get(
            self.url,
            {"q": "testing"},
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)
        self.assertEqual(resp.context_data["page_obj"].object_list[0], episode)


class EpisodeDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.episode = EpisodeFactory()

    def test_detail(self) -> None:
        resp = self.client.get(self.episode.get_absolute_url())
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context_data["episode"], self.episode)


class PreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.episode = EpisodeFactory()

    def test_preview(self) -> None:
        resp = self.client.get(
            reverse("episodes:preview", args=[self.episode.id]),
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)


class ActionsTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.episode = EpisodeFactory()
        cls.user = UserFactory()

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_actions(self) -> None:
        resp = self.client.get(
            reverse("episodes:actions", args=[self.episode.id]),
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context_data["episode"], self.episode)


class StartPlayerTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_play_from_start(self) -> None:
        resp = self.client.post(
            reverse("episodes:start_player", args=[self.episode.id])
        )

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)

    def test_play_episode_in_history(self) -> None:
        AudioLogFactory(user=self.user, episode=self.episode, current_time=2000)
        resp = self.client.post(
            reverse("episodes:start_player", args=[self.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)


class PlayNextEpisodeTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def setUp(self) -> None:
        self.url = reverse("episodes:play_next_episode")
        self.client.force_login(self.user)

    def test_has_next_in_queue(self) -> None:
        QueueItem.objects.create(position=0, user=self.user, episode=self.episode)
        resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(QueueItem.objects.count(), 0)

    def test_has_episode_in_player(self) -> None:

        log = AudioLogFactory(user=self.user, current_time=2000)

        session = self.client.session
        session.update({"player": {"episode": log.episode.id, "current_time": 1000}})
        session.save()

        resp = self.client.post(reverse("episodes:play_next_episode"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)

    def test_play_next_episode_in_history(self) -> None:
        log = AudioLogFactory(user=self.user, current_time=30)

        QueueItem.objects.create(position=0, user=self.user, episode=log.episode)
        resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(QueueItem.objects.count(), 0)

    def test_queue_empty(self) -> None:
        resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(QueueItem.objects.count(), 0)


class ClosePlayerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):

        self.client.force_login(self.user)

    def test_stop_if_player_empty(self) -> None:
        resp = self.client.post(
            reverse("episodes:close_player"),
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)

    def test_stop(self) -> None:
        episode = EpisodeFactory()

        session = self.client.session
        session.update({"player": {"episode": episode.id, "current_time": 1000}})
        session.save()

        AudioLogFactory(user=self.user, episode=episode, current_time=2000)
        resp = self.client.post(
            reverse("episodes:close_player"),
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)


class PlayerTimeUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()
        cls.url = reverse("episodes:player_time_update")

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_is_running(self) -> None:
        log = AudioLogFactory(user=self.user, episode=self.episode)

        session = self.client.session
        session["player_episode"] = self.episode.id
        session.save()

        resp = self.client.post(
            self.url,
            {"current_time": "1030.0001"},
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)

        log.refresh_from_db()
        self.assertEqual(log.current_time, 1030)

    def test_player_not_running(self) -> None:
        resp = self.client.post(
            self.url,
            {"current_time": "1030.0001"},
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)

    def test_missing_data(self) -> None:
        session = self.client.session
        session["player_episode"] = self.episode.id
        session.save()

        resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, http.HTTPStatus.BAD_REQUEST)

    def test_invalid_data(self) -> None:
        session = self.client.session
        session["player_episode"] = self.episode.id
        session.save()

        resp = self.client.post(self.url, {"current_time": "xyz"})
        self.assertEqual(resp.status_code, http.HTTPStatus.BAD_REQUEST)


class HistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_get(self) -> None:
        AudioLogFactory.create_batch(3, user=self.user)
        resp = self.client.get(reverse("episodes:history"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 3)

    def test_search(self) -> None:

        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            AudioLogFactory(
                user=self.user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        AudioLogFactory(user=self.user, episode=EpisodeFactory(title="testing"))
        resp = self.client.get(reverse("episodes:history"), {"q": "testing"})
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)


class FavoritesTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_get(self) -> None:
        FavoriteFactory.create_batch(3, user=self.user)
        resp = self.client.get(reverse("episodes:favorites"))

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 3)

    def test_search(self) -> None:

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
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)


class AddFavoriteTests(TransactionTestCase):
    def setUp(self) -> None:
        self.user = UserFactory()
        self.episode = EpisodeFactory()
        self.client.force_login(self.user)

    def test_post(self) -> None:
        resp = self.client.post(
            reverse("episodes:add_favorite", args=[self.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)
        self.assertTrue(
            Favorite.objects.filter(user=self.user, episode=self.episode).exists()
        )

    def test_already_favorite(self) -> None:
        FavoriteFactory(episode=self.episode, user=self.user)
        resp = self.client.post(
            reverse("episodes:add_favorite", args=[self.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)
        self.assertTrue(
            Favorite.objects.filter(user=self.user, episode=self.episode).exists()
        )


class RemoveFavoriteTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.episode = EpisodeFactory()

    def test_post(self) -> None:
        user = UserFactory()
        self.client.force_login(user)
        FavoriteFactory(user=user, episode=self.episode)
        resp = self.client.post(
            reverse("episodes:remove_favorite", args=[self.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)
        self.assertFalse(
            Favorite.objects.filter(user=user, episode=self.episode).exists()
        )


class RemoveAudioLogTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def setUp(self) -> None:
        self.url = reverse("episodes:remove_audio_log", args=[self.episode.id])
        self.client.force_login(self.user)

    def test_ok(self) -> None:
        AudioLogFactory(user=self.user, episode=self.episode)
        AudioLogFactory(user=self.user)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)

        self.assertFalse(
            AudioLog.objects.filter(user=self.user, episode=self.episode).exists()
        )
        self.assertEqual(AudioLog.objects.filter(user=self.user).count(), 1)

    def test_is_playing(self) -> None:
        """Do not remove log if episode is currently playing"""
        AudioLogFactory(user=self.user, episode=self.episode)

        session = self.client.session
        session["player_episode"] = self.episode.id
        session.save()

        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, http.HTTPStatus.BAD_REQUEST)
        self.assertTrue(
            AudioLog.objects.filter(user=self.user, episode=self.episode).exists()
        )

    def test_none_remaining(self) -> None:
        AudioLogFactory(user=self.user, episode=self.episode)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)
        self.assertFalse(
            AudioLog.objects.filter(user=self.user, episode=self.episode).exists()
        )
        self.assertEqual(AudioLog.objects.filter(user=self.user).count(), 0)


class QueueTests(TestCase):
    def test_get(self) -> None:
        user = UserFactory()
        self.client.force_login(user)

        QueueItemFactory.create_batch(3, user=user)
        resp = self.client.get(reverse("episodes:queue"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)


class AddToQueueTests(TransactionTestCase):
    add_to_start_url = "episodes:add_to_queue_start"
    add_to_end_url = "episodes:add_to_queue_end"

    def setUp(self) -> None:
        self.user = UserFactory()
        self.episode = EpisodeFactory()

        self.client.force_login(self.user)

    def test_add_to_queue_end(self) -> None:
        first = EpisodeFactory()
        second = EpisodeFactory()
        third = EpisodeFactory()

        for episode in (first, second, third):
            resp = self.client.post(reverse(self.add_to_end_url, args=[episode.id]))
            self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)

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

    def test_add_to_queue_start(self) -> None:
        first = EpisodeFactory()
        second = EpisodeFactory()
        third = EpisodeFactory()

        for episode in (first, second, third):
            resp = self.client.post(
                reverse(
                    self.add_to_start_url,
                    args=[episode.id],
                ),
            )
            self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)

        items = (
            QueueItem.objects.filter(user=self.user)
            .select_related("episode")
            .order_by("position")
        )

        self.assertEqual(items[0].episode, third)
        self.assertEqual(items[0].position, 1)

        self.assertEqual(items[1].episode, second)
        self.assertEqual(items[1].position, 2)

        self.assertEqual(items[2].episode, first)
        self.assertEqual(items[2].position, 3)

    def test_is_playing(self) -> None:
        session = self.client.session
        session["player_episode"] = self.episode.id
        session.save()
        resp = self.client.post(
            reverse(
                self.add_to_start_url,
                args=[self.episode.id],
            ),
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.BAD_REQUEST)
        self.assertEqual(QueueItem.objects.count(), 0)

    def test_already_queued(self) -> None:
        QueueItemFactory(episode=self.episode, user=self.user)
        resp = self.client.post(
            reverse(
                self.add_to_start_url,
                args=[self.episode.id],
            ),
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)


class RemoveFromQueueTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.episode = EpisodeFactory()

    def test_post(self) -> None:
        user = UserFactory()
        self.client.force_login(user)
        item = QueueItemFactory(user=user)
        resp = self.client.post(
            reverse("episodes:remove_from_queue", args=[item.episode.id])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.NO_CONTENT)
        self.assertEqual(QueueItem.objects.filter(user=user).count(), 0)


class TestMoveQueueItems(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_post(self) -> None:

        first = QueueItemFactory(user=self.user)
        second = QueueItemFactory(user=self.user)
        third = QueueItemFactory(user=self.user)

        items = QueueItem.objects.filter(user=self.user).order_by("position")

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

        items = QueueItem.objects.filter(user=self.user).order_by("position")

        self.assertEqual(items[0], third)
        self.assertEqual(items[1], first)
        self.assertEqual(items[2], second)

    def test_invalid(self) -> None:
        resp = self.client.post(
            reverse("episodes:move_queue_items"), {"items": "incorrect"}
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.BAD_REQUEST)
