import uuid

import pytest

from django.urls import reverse, reverse_lazy
from django.utils import timezone

from jcasts.episodes.factories import EpisodeFactory
from jcasts.podcasts.factories import (
    FollowFactory,
    PodcastFactory,
    RecommendationFactory,
)
from jcasts.podcasts.models import Follow
from jcasts.podcasts.podcastindex import Feed
from jcasts.shared.assertions import assert_conflict, assert_not_found, assert_ok

podcasts_url = reverse_lazy("podcasts:index")


class TestPodcasts:
    def test_anonymous(self, client, db, django_assert_num_queries):
        PodcastFactory.create_batch(3, promoted=True)
        with django_assert_num_queries(3):
            resp = client.get(podcasts_url)
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_is_following_promoted(
        self, client, auth_user, django_assert_num_queries
    ):
        """If user is not following any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        sub = FollowFactory(user=auth_user).podcast
        with django_assert_num_queries(7):
            resp = client.get(reverse("podcasts:index"), {"promoted": True})
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3
        assert sub not in resp.context_data["page_obj"].object_list

    def test_user_is_not_following(self, client, auth_user, django_assert_num_queries):
        """If user is not following any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        with django_assert_num_queries(7):
            resp = client.get(podcasts_url)
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_is_following(self, client, auth_user, django_assert_num_queries):
        """If user following any podcasts, show only own feed with these podcasts"""

        PodcastFactory.create_batch(3)
        sub = FollowFactory(user=auth_user)
        with django_assert_num_queries(7):
            resp = client.get(podcasts_url)
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == sub.podcast


class TestLatest:
    def url(self, podcast):
        return reverse("podcasts:latest", args=[podcast.id])

    def test_has_no_episodes(self, client, podcast, django_assert_num_queries):
        with django_assert_num_queries(3):
            resp = client.get(self.url(podcast))
        assert resp.url == podcast.get_absolute_url()

    def test_has_episodes(self, client, episode, django_assert_num_queries):
        with django_assert_num_queries(3):
            resp = client.get(self.url(episode.podcast))
        assert resp.url == episode.get_absolute_url()


class TestSearchPodcasts:
    def test_search_empty(self, client, db, django_assert_num_queries):
        with django_assert_num_queries(1):
            assert (
                client.get(
                    reverse("podcasts:search_podcasts"),
                    {"q": ""},
                ).url
                == podcasts_url
            )

    def test_search(self, client, db, faker, django_assert_num_queries):
        podcast = PodcastFactory(title=faker.unique.text())
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        with django_assert_num_queries(3):
            resp = client.get(
                reverse("podcasts:search_podcasts"),
                {"q": podcast.title},
            )
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == podcast


class TestSearchPodcastIndex:
    def test_search(self, client, db, mocker, django_assert_num_queries):
        feeds = [
            Feed(
                url="https://feeds.fireside.fm/testandcode/rss",
                title="Test & Code : Python Testing",
                image="https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
            )
        ]
        mock_search = mocker.patch(
            "jcasts.podcasts.podcastindex.search", return_value=feeds
        )

        with django_assert_num_queries(1):
            resp = client.get(reverse("podcasts:search_podcastindex"), {"q": "test"})
        assert_ok(resp)

        mock_search.assert_called()


class TestPodcastRecommendations:
    def test_get(self, client, db, podcast, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        with django_assert_num_queries(5):
            resp = client.get(
                reverse(
                    "podcasts:podcast_recommendations", args=[podcast.id, podcast.slug]
                )
            )
        assert_ok(resp)
        assert resp.context_data["podcast"] == podcast
        assert len(resp.context_data["recommendations"]) == 3


class TestPodcastDetail:
    def test_get_podcast_anonymous(self, client, podcast, django_assert_num_queries):
        with django_assert_num_queries(5):
            resp = client.get(
                reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
            )
        assert_ok(resp)
        assert resp.context_data["podcast"] == podcast

    def test_get_podcast_authenticated(
        self, client, auth_user, podcast, django_assert_num_queries
    ):
        with django_assert_num_queries(9):
            resp = client.get(
                reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
            )
        assert_ok(resp)
        assert resp.context_data["podcast"] == podcast


class TestPodcastEpisodes:
    def test_get_episodes(self, client, podcast, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)

        with django_assert_num_queries(6):
            resp = client.get(
                reverse(
                    "podcasts:podcast_episodes",
                    args=[podcast.id, podcast.slug],
                )
            )
            assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_get_oldest_first(self, client, podcast, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)

        with django_assert_num_queries(6):
            resp = client.get(
                reverse(
                    "podcasts:podcast_episodes",
                    args=[podcast.id, podcast.slug],
                ),
                {"ordering": "asc"},
            )
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self, client, podcast, faker, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)

        episode = EpisodeFactory(title=faker.unique.name(), podcast=podcast)

        with django_assert_num_queries(6):
            resp = client.get(
                reverse(
                    "podcasts:podcast_episodes",
                    args=[podcast.id, podcast.slug],
                ),
                {"q": episode.title},
            )
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestCategoryDetail:
    def test_get(self, client, category, django_assert_num_queries):
        PodcastFactory.create_batch(12, categories=[category])
        with django_assert_num_queries(4):
            resp = client.get(category.get_absolute_url())
        assert_ok(resp)
        assert resp.context_data["category"] == category

    def test_search(self, client, category, faker, django_assert_num_queries):

        PodcastFactory.create_batch(
            12, title="zzzz", keywords="zzzz", categories=[category]
        )
        podcast = PodcastFactory(title=faker.unique.text(), categories=[category])

        with django_assert_num_queries(4):
            resp = client.get(category.get_absolute_url(), {"q": podcast.title})
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestFollow:
    @pytest.fixture
    def url(self, podcast):
        return reverse("podcasts:follow", args=[podcast.id])

    def test_follow(self, client, podcast, auth_user, url, django_assert_num_queries):
        with django_assert_num_queries(5):
            resp = client.post(url, {"render": True})
        assert_ok(resp)
        assert Follow.objects.filter(podcast=podcast, user=auth_user).exists()

    @pytest.mark.django_db(transaction=True)
    def test_already_following(
        self, client, podcast, auth_user, url, django_assert_num_queries
    ):

        FollowFactory(user=auth_user, podcast=podcast)
        with django_assert_num_queries(5):
            resp = client.post(url)
        assert_conflict(resp)
        assert Follow.objects.filter(podcast=podcast, user=auth_user).exists()


class TestUnfollow:
    def test_unfollow(self, client, auth_user, podcast, django_assert_num_queries):
        FollowFactory(user=auth_user, podcast=podcast)
        with django_assert_num_queries(5):
            resp = client.post(reverse("podcasts:unfollow", args=[podcast.id]))
        assert_ok(resp)
        assert not Follow.objects.filter(podcast=podcast, user=auth_user).exists()


class TestWebsubSubscribe:
    hub = "https://pubsubhubbub.appspot.com/"
    challenge = "12345abcd"
    lease_seconds = 3600

    def url(self, podcast):
        return reverse("podcasts:websub_subscribe", args=[podcast.websub_token])

    def test_get_ok(self, db, client):
        podcast = PodcastFactory(websub_hub=self.hub, websub_token=uuid.uuid4())
        resp = client.get(
            self.url(podcast),
            {
                "hub.mode": "subscribe",
                "hub.topic": podcast.rss,
                "hub.challenge": self.challenge,
                "hub.lease_seconds": self.lease_seconds,
            },
        )
        assert_ok(resp)
        assert resp.content == bytes(self.challenge, "utf-8")

        podcast.refresh_from_db()

        assert (
            timezone.now() - podcast.websub_subscribed
        ).total_seconds() == pytest.approx(self.lease_seconds, 10)

    def test_missing_mode(self, db, client):
        podcast = PodcastFactory(websub_hub=self.hub, websub_token=uuid.uuid4())
        resp = client.get(
            self.url(podcast),
            {
                "hub.topic": podcast.rss,
                "hub.challenge": self.challenge,
                "hub.lease_seconds": self.lease_seconds,
            },
        )
        assert_not_found(resp)

        podcast.refresh_from_db()
        assert podcast.websub_exception
        assert not podcast.websub_subscribed

    def test_invalid_mode(self, db, client):
        podcast = PodcastFactory(websub_hub=self.hub, websub_token=uuid.uuid4())
        resp = client.get(
            self.url(podcast),
            {
                "hub.mode": "unsubscribe",
                "hub.topic": podcast.rss,
                "hub.challenge": self.challenge,
                "hub.lease_seconds": self.lease_seconds,
            },
        )
        assert_not_found(resp)
        podcast.refresh_from_db()
        assert podcast.websub_exception
        assert not podcast.websub_subscribed

    def test_invalid_lease_seconds(self, db, client):
        podcast = PodcastFactory(websub_hub=self.hub, websub_token=uuid.uuid4())
        resp = client.get(
            self.url(podcast),
            {
                "hub.mode": "subscribe",
                "hub.topic": podcast.rss,
                "hub.challenge": self.challenge,
                "hub.lease_seconds": "test",
            },
        )
        assert_not_found(resp)

    def test_missing_topic(self, db, client):
        podcast = PodcastFactory(websub_hub=self.hub, websub_token=uuid.uuid4())
        resp = client.get(
            self.url(podcast),
            {
                "hub.mode": "subscribe",
                "hub.challenge": self.challenge,
                "hub.lease_seconds": self.lease_seconds,
            },
        )
        assert_not_found(resp)
        podcast.refresh_from_db()
        assert podcast.websub_exception
        assert not podcast.websub_subscribed

    def test_invalid_topic(self, db, client):
        podcast = PodcastFactory(websub_hub=self.hub, websub_token=uuid.uuid4())
        resp = client.get(
            self.url(podcast),
            {
                "hub.mode": "subscribe",
                "hub.topic": "https://random.com/test.rss",
                "hub.challenge": self.challenge,
                "hub.lease_seconds": self.lease_seconds,
            },
        )
        assert_not_found(resp)
        podcast.refresh_from_db()
        assert podcast.websub_exception
        assert not podcast.websub_subscribed

    def test_post_ok(self, db, client, mocker):
        class MockQueue:
            def enqueue(self, func, *args, **kwargs):
                pass

        mock_queue = mocker.patch("jcasts.podcasts.views.get_queue")
        podcast = PodcastFactory(websub_hub=self.hub, websub_token=uuid.uuid4())
        resp = client.post(self.url(podcast))
        assert_ok(resp)
        mock_queue.assert_called()
