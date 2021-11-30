import uuid

import pytest

from django.urls import reverse, reverse_lazy
from django.utils import timezone

from jcasts.episodes.factories import EpisodeFactory
from jcasts.podcasts import websub
from jcasts.podcasts.factories import (
    FollowFactory,
    PodcastFactory,
    RecommendationFactory,
)
from jcasts.podcasts.itunes import Feed
from jcasts.podcasts.models import Follow, Podcast
from jcasts.shared.assertions import (
    assert_bad_request,
    assert_conflict,
    assert_no_content,
    assert_not_found,
    assert_ok,
)

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
        with django_assert_num_queries(6):
            resp = client.get(reverse("podcasts:index"), {"promoted": True})
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3
        assert sub not in resp.context_data["page_obj"].object_list

    def test_user_is_not_following(self, client, auth_user, django_assert_num_queries):
        """If user is not following any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        with django_assert_num_queries(6):
            resp = client.get(podcasts_url)
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_is_following(self, client, auth_user, django_assert_num_queries):
        """If user following any podcasts, show only own feed with these podcasts"""

        PodcastFactory.create_batch(3)
        sub = FollowFactory(user=auth_user)
        with django_assert_num_queries(6):
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


class TestActions:
    def url(self, podcast):
        return reverse("podcasts:actions", args=[podcast.id])

    def test_has_no_episodes(self, client, podcast, django_assert_num_queries):
        with django_assert_num_queries(3):
            resp = client.get(self.url(podcast))
        assert_not_found(resp)

    def test_has_episodes(self, client, episode, django_assert_num_queries):
        with django_assert_num_queries(3):
            resp = client.get(self.url(episode.podcast))
        assert_ok(resp)


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


class TestSearchAutocomplete:
    url = reverse_lazy("podcasts:search_autocomplete")

    def test_search_empty(self, client, db, django_assert_num_queries):
        with django_assert_num_queries(1):
            assert_ok(client.get(self.url, {"q": ""}))

    def test_search_podcast_only(self, client, db, faker, django_assert_num_queries):
        podcast = PodcastFactory(title=faker.unique.text())
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        with django_assert_num_queries(3):
            resp = client.get(self.url, {"q": podcast.title})
        assert_ok(resp)
        assert len(resp.context_data["podcasts"]) == 1
        assert len(resp.context_data["episodes"]) == 0

    def test_search_episode_only(self, client, db, faker, django_assert_num_queries):
        episode = EpisodeFactory(title=faker.unique.text())
        with django_assert_num_queries(3):
            resp = client.get(self.url, {"q": episode.title})
        assert_ok(resp)
        assert len(resp.context_data["podcasts"]) == 0
        assert len(resp.context_data["episodes"]) == 1

    def test_search_podcast_and_episode(
        self, client, db, faker, django_assert_num_queries
    ):
        podcast = PodcastFactory(title=faker.unique.text())
        EpisodeFactory(title=podcast.title)
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        with django_assert_num_queries(3):
            resp = client.get(self.url, {"q": podcast.title})
        assert_ok(resp)
        assert len(resp.context_data["podcasts"]) == 1
        assert len(resp.context_data["episodes"]) == 1


class TestSearchITunes:
    def test_search(self, client, db, mocker, django_assert_num_queries):
        feeds = [
            Feed(
                url="https://feeds.fireside.fm/testandcode/rss",
                title="Test & Code : Py4hon Testing",
                image="https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
            )
        ]
        mock_search = mocker.patch("jcasts.podcasts.itunes.search", return_value=feeds)

        with django_assert_num_queries(1):
            resp = client.get(reverse("podcasts:search_itunes"), {"q": "test"})
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
        with django_assert_num_queries(8):
            resp = client.get(
                reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
            )
        assert_ok(resp)
        assert resp.context_data["podcast"] == podcast


class TestPodcastEpisodes:
    def url(self, podcast):
        return reverse(
            "podcasts:podcast_episodes",
            args=[podcast.id, podcast.slug],
        )

    def test_get_episodes(self, client, podcast, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)

        with django_assert_num_queries(6):
            resp = client.get(self.url(podcast))
            assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_get_oldest_first(self, client, podcast, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)

        with django_assert_num_queries(6):
            resp = client.get(
                self.url(podcast),
                {"ordering": "asc"},
            )
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self, client, podcast, faker, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)

        episode = EpisodeFactory(title=faker.unique.name(), podcast=podcast)

        with django_assert_num_queries(6):
            resp = client.get(
                self.url(podcast),
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
            resp = client.post(url)
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


class TestWebSubCallback:

    topic = "https://podnews.net/rss"

    def test_post(self, db, client, django_assert_num_queries, mock_parse_podcast_feed):

        podcast = PodcastFactory(
            websub_mode="subscribe",
            websub_token=uuid.uuid4(),
            websub_status=Podcast.WebSubStatus.ACTIVE,
            websub_secret=uuid.uuid4(),
        )
        sig = websub.make_signature(podcast.websub_secret, b"testing", "sha1")

        with django_assert_num_queries(3):
            assert_no_content(
                client.post(
                    self.url(podcast),
                    data=b"testing",
                    content_type="application/xml",
                    HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
                )
            )

        mock_parse_podcast_feed.assert_called_with(podcast.id)

    def test_post_inactive(
        self, db, client, django_assert_num_queries, mock_parse_podcast_feed
    ):

        podcast = PodcastFactory(
            websub_mode="subscribe",
            websub_token=uuid.uuid4(),
            websub_status=Podcast.WebSubStatus.INACTIVE,
            websub_secret=uuid.uuid4(),
        )
        sig = websub.make_signature(podcast.websub_secret, b"testing", "sha1")

        with django_assert_num_queries(2):
            assert_not_found(
                client.post(
                    self.url(podcast),
                    data=b"testing",
                    content_type="application/xml",
                    HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
                )
            )

        mock_parse_podcast_feed.assert_not_called()

    def test_post_bad_sig(
        self, db, client, django_assert_num_queries, mock_parse_podcast_feed
    ):

        podcast = PodcastFactory(
            websub_mode="subscribe",
            websub_token=uuid.uuid4(),
            websub_status=Podcast.WebSubStatus.ACTIVE,
            websub_secret=uuid.uuid4(),
        )
        sig = websub.make_signature(uuid.uuid4(), b"testing", "sha1")

        with django_assert_num_queries(3):
            assert_bad_request(
                client.post(
                    self.url(podcast),
                    data=b"testing",
                    content_type="application/xml",
                    HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
                )
            )

        mock_parse_podcast_feed.assert_not_called()
        podcast.refresh_from_db()
        assert podcast.websub_status_changed
        assert podcast.websub_exception
        assert podcast.websub_status == Podcast.WebSubStatus.ERROR

    def test_subscribe(self, db, client, django_assert_num_queries):
        podcast = PodcastFactory(
            websub_mode="subscribe",
            websub_token=uuid.uuid4(),
            websub_url=self.topic,
            websub_status=Podcast.WebSubStatus.REQUESTED,
        )
        with django_assert_num_queries(3):
            assert_ok(
                client.get(
                    self.url(podcast),
                    {
                        "hub.mode": "subscribe",
                        "hub.topic": self.topic,
                        "hub.challenge": "ok",
                        "hub.lease_seconds": 7 * 24 * 60 * 60,
                    },
                )
            )

        podcast.refresh_from_db()

        assert podcast.websub_status_changed
        assert podcast.websub_status == Podcast.WebSubStatus.ACTIVE
        assert (podcast.websub_timeout - timezone.now()).days == 6

    def test_subscribe_invalid_mode(self, db, client, django_assert_num_queries):
        podcast = PodcastFactory(
            websub_mode="subscribe",
            websub_token=uuid.uuid4(),
            websub_url=self.topic,
            websub_status=Podcast.WebSubStatus.REQUESTED,
        )
        with django_assert_num_queries(3):
            assert_not_found(
                client.get(
                    self.url(podcast),
                    {
                        "hub.mode": "unsubscribe",
                        "hub.topic": self.topic,
                        "hub.challenge": "ok",
                        "hub.lease_seconds": 7 * 24 * 60 * 60,
                    },
                )
            )

        podcast.refresh_from_db()

        assert podcast.websub_status_changed
        assert podcast.websub_exception
        assert podcast.websub_status == Podcast.WebSubStatus.ERROR

    def test_subscribe_invalid_topic(self, db, client, django_assert_num_queries):
        podcast = PodcastFactory(
            websub_mode="subscribe",
            websub_token=uuid.uuid4(),
            websub_url=self.topic,
            websub_status=Podcast.WebSubStatus.REQUESTED,
        )
        with django_assert_num_queries(3):
            assert_not_found(
                client.get(
                    self.url(podcast),
                    {
                        "hub.mode": "subscribe",
                        "hub.topic": "https://other-topic.com/",
                        "hub.challenge": "ok",
                        "hub.lease_seconds": 7 * 24 * 60 * 60,
                    },
                )
            )

        podcast.refresh_from_db()

        assert podcast.websub_status_changed
        assert podcast.websub_exception
        assert podcast.websub_status == Podcast.WebSubStatus.ERROR

    def test_subscribe_missing_mode(self, db, client, django_assert_num_queries):
        podcast = PodcastFactory(
            websub_mode="subscribe",
            websub_token=uuid.uuid4(),
            websub_url=self.topic,
            websub_status=Podcast.WebSubStatus.REQUESTED,
        )
        with django_assert_num_queries(3):
            assert_not_found(
                client.get(
                    self.url(podcast),
                    {
                        "hub.topic": self.topic,
                        "hub.challenge": "ok",
                        "hub.lease_seconds": 7 * 24 * 60 * 60,
                    },
                )
            )

        podcast.refresh_from_db()

        assert podcast.websub_status_changed
        assert podcast.websub_exception
        assert podcast.websub_status == Podcast.WebSubStatus.ERROR

    def test_subscribe_not_requested_status(
        self, db, client, django_assert_num_queries
    ):
        podcast = PodcastFactory(
            websub_mode="subscribe",
            websub_url=self.topic,
            websub_token=uuid.uuid4(),
            websub_status=Podcast.WebSubStatus.ACTIVE,
        )
        with django_assert_num_queries(2):
            assert_not_found(
                client.get(
                    self.url(podcast),
                    {
                        "hub.mode": "subscribe",
                        "hub.topic": self.topic,
                        "hub.challenge": "ok",
                        "hub.lease_seconds": 7 * 24 * 60 * 60,
                    },
                )
            )

        podcast.refresh_from_db()

        assert podcast.websub_status == Podcast.WebSubStatus.ACTIVE

    def test_subscribe_missing_lease_seconds(
        self, db, client, django_assert_num_queries
    ):
        podcast = PodcastFactory(
            websub_mode="subscribe",
            websub_url=self.topic,
            websub_token=uuid.uuid4(),
            websub_status=Podcast.WebSubStatus.REQUESTED,
        )
        with django_assert_num_queries(3):
            assert_not_found(
                client.get(
                    self.url(podcast),
                    {
                        "hub.mode": "subscribe",
                        "hub.topic": self.topic,
                        "hub.challenge": "ok",
                    },
                )
            )

        podcast.refresh_from_db()

        assert podcast.websub_status_changed
        assert podcast.websub_exception
        assert podcast.websub_status == Podcast.WebSubStatus.ERROR

    def test_unsubscribe(self, db, client, django_assert_num_queries):
        podcast = PodcastFactory(
            websub_mode="unsubscribe",
            websub_token=uuid.uuid4(),
            websub_url=self.topic,
            websub_status=Podcast.WebSubStatus.REQUESTED,
        )
        with django_assert_num_queries(3):
            assert_ok(
                client.get(
                    self.url(podcast),
                    {
                        "hub.mode": "unsubscribe",
                        "hub.topic": self.topic,
                        "hub.challenge": "ok",
                    },
                )
            )

        podcast.refresh_from_db()

        assert podcast.websub_status_changed
        assert podcast.websub_status == Podcast.WebSubStatus.INACTIVE

    def url(self, podcast):
        return reverse("podcasts:websub_callback", args=[podcast.websub_token])
