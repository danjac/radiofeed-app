import json
import pathlib
import uuid

from unittest.mock import Mock, patch

import requests

from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.test import RequestFactory, SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone

from audiotrails.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
)
from audiotrails.episodes.models import Episode
from audiotrails.podcasts.factories import (
    CategoryFactory,
    FollowFactory,
    PodcastFactory,
    RecommendationFactory,
)
from audiotrails.podcasts.models import (
    Category,
    Podcast,
    Recommendation,
    get_categories_dict,
)
from audiotrails.users.factories import UserFactory


class RecommendationManagerTests(TestCase):
    def test_bulk_delete(self) -> None:
        RecommendationFactory.create_batch(3)
        Recommendation.objects.bulk_delete()
        self.assertEqual(Recommendation.objects.count(), 0)

    def test_for_user(self) -> None:

        user = UserFactory()
        following = FollowFactory(user=user).podcast
        favorited = FavoriteFactory(user=user).episode.podcast
        listened = AudioLogFactory(user=user).episode.podcast

        received = RecommendationFactory(
            podcast=FollowFactory(user=user).podcast
        ).recommended
        user.recommended_podcasts.add(received)

        first = RecommendationFactory(podcast=following).recommended
        second = RecommendationFactory(podcast=favorited).recommended
        third = RecommendationFactory(podcast=listened).recommended

        # already received

        # not connected
        RecommendationFactory()

        # already following, listened to or favorited
        RecommendationFactory(recommended=following)
        RecommendationFactory(recommended=favorited)
        RecommendationFactory(recommended=listened)

        recommended = [r.recommended for r in Recommendation.objects.for_user(user)]

        self.assertEqual(len(recommended), 3)
        self.assertTrue(first in recommended)
        self.assertTrue(second in recommended)
        self.assertTrue(third in recommended)


class CategoryManagerTests(TestCase):
    def test_search(self) -> None:
        CategoryFactory(name="testing")
        self.assertEqual(Category.objects.search("testing").count(), 1)


class CategoryModelTests(SimpleTestCase):
    def test_slug(self) -> None:
        category = Category(name="Testing")
        self.assertEqual(category.slug, "testing")


class PodcastManagerSearchTests(TransactionTestCase):
    def test_search(self) -> None:
        PodcastFactory(title="testing")
        self.assertEqual(Podcast.objects.search("testing").count(), 1)


class PodcastManagerTests(TestCase):
    def test_with_follow_count(self):
        following_1 = PodcastFactory()
        following_2 = PodcastFactory()
        not_following = PodcastFactory()

        FollowFactory(podcast=following_1)
        FollowFactory(podcast=following_1)
        FollowFactory(podcast=following_2)

        podcasts = Podcast.objects.with_follow_count().order_by("-follow_count")

        self.assertEqual(podcasts[0].id, following_1.id)
        self.assertEqual(podcasts[1].id, following_2.id)
        self.assertEqual(podcasts[2].id, not_following.id)

        self.assertEqual(podcasts[0].follow_count, 2)
        self.assertEqual(podcasts[1].follow_count, 1)
        self.assertEqual(podcasts[2].follow_count, 0)


class PodcastModelTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.podcast = PodcastFactory(title="Testing")
        cls.user = UserFactory()

    def test_slug(self) -> None:
        self.assertEqual(self.podcast.slug, "testing")

    def test_get_episode_count(self) -> None:
        EpisodeFactory.create_batch(3)
        EpisodeFactory.create_batch(3, podcast=self.podcast)
        self.assertEqual(self.podcast.get_episode_count(), 3)

    def test_get_cached_episode_count(self) -> None:
        EpisodeFactory.create_batch(3)
        EpisodeFactory.create_batch(3, podcast=self.podcast)
        self.assertEqual(self.podcast.get_cached_episode_count(), 3)

    def test_slug_if_title_empty(self) -> None:
        self.assertEqual(Podcast().slug, "podcast")

    def is_following_anonymous(self) -> None:
        self.assertFalse(self.podcast.is_following(AnonymousUser()))

    def is_following_false(self) -> None:
        self.assertFalse(self.podcast.is_following(UserFactory()))

    def is_following_true(self) -> None:
        sub = FollowFactory(podcast=self.podcast)
        self.assertTrue(self.podcast.is_following(sub.user))

    def test_get_opengraph_data(self) -> None:
        req = RequestFactory().get("/")
        req.site = Site.objects.get_current()
        og_data = self.podcast.get_opengraph_data(req)
        self.assertTrue(self.podcast.title in og_data["title"])
        self.assertEqual(
            og_data["url"], "http://testserver" + self.podcast.get_absolute_url()
        )


class BaseMockResponse:
    def __init__(self, raises: bool = False):
        self.raises = raises

    def raise_for_status(self) -> None:
        if self.raises:
            raise requests.exceptions.HTTPError()


class MockHeaderResponse(BaseMockResponse):
    def __init__(self):
        super().__init__()
        self.headers = {
            "ETag": uuid.uuid4().hex,
            "Last-Modified": "Sun, 05 Jul 2020 19:21:33 GMT",
        }


class MockResponse(BaseMockResponse):
    def __init__(self, mock_file: str = None, raises: bool = False):
        super().__init__(raises)
        self.headers = {
            "ETag": uuid.uuid4().hex,
            "Last-Modified": "Sun, 05 Jul 2020 19:21:33 GMT",
        }

        if mock_file:
            self.content = open(
                pathlib.Path(__file__).parent / "mocks" / mock_file, "rb"
            ).read()
        self.raises = raises

    def json(self) -> str:
        return json.loads(self.content)


class PodcastsRssSyncTests(TestCase):

    rss = "https://mysteriousuniverse.org/feed/podcast/"

    def tearDown(self) -> None:
        get_categories_dict.cache_clear()

    @patch("requests.head", autospec=True, side_effect=requests.RequestException)
    def test_parse_error(self, *mocks: Mock) -> None:
        podcast = PodcastFactory()
        self.assertRaises(requests.RequestException, podcast.sync_rss_feed)
        podcast.refresh_from_db()
        self.assertEqual(podcast.num_retries, 1)

    @patch("requests.head", autospec=True, return_value=MockHeaderResponse())
    @patch("requests.get", autospec=True, return_value=MockResponse("rss_mock.xml"))
    def test_parse(self, *mocks: Mock) -> None:
        [
            CategoryFactory(name=name)
            for name in (
                "Philosophy",
                "Science",
                "Social Sciences",
                "Society & Culture",
                "Spirituality",
                "Religion & Spirituality",
            )
        ]
        podcast = PodcastFactory(
            rss=self.rss,
            last_updated=None,
            pub_date=None,
        )
        self.assertTrue(podcast.sync_rss_feed())
        podcast.refresh_from_db()

        self.assertTrue(podcast.last_updated)
        self.assertTrue(podcast.pub_date)

        self.assertTrue(podcast.etag)
        self.assertTrue(podcast.cover_image)
        self.assertTrue(podcast.extracted_text)

        self.assertEqual(podcast.title, "Mysterious Universe")
        self.assertEqual(podcast.creators, "8th Kind")
        self.assertEqual(podcast.categories.count(), 6)
        self.assertEqual(podcast.episode_set.count(), 20)

    @patch("requests.head", autospec=True, return_value=MockHeaderResponse())
    @patch("requests.get", autospec=True, return_value=MockResponse("rss_mock.xml"))
    def test_parse_if_already_updated(self, *mocks: Mock) -> None:
        podcast = PodcastFactory(
            rss=self.rss,
            last_updated=timezone.now(),
            cover_image=None,
            pub_date=None,
        )

        self.assertEqual(podcast.sync_rss_feed(), [])
        podcast.refresh_from_db()

        self.assertFalse(podcast.pub_date)
        self.assertFalse(podcast.cover_image)

        self.assertNotEqual(podcast.title, "Mysterious Universe")
        self.assertEqual(podcast.episode_set.count(), 0)

    @patch("requests.head", autospec=True, return_value=MockHeaderResponse())
    @patch("requests.get", autospec=True, return_value=MockResponse("rss_mock.xml"))
    def test_parse_existing_episodes(self, *mocks: Mock) -> None:
        podcast = PodcastFactory(
            rss=self.rss,
            last_updated=None,
            pub_date=None,
        )

        EpisodeFactory(podcast=podcast, guid="https://mysteriousuniverse.org/?p=168097")
        EpisodeFactory(podcast=podcast, guid="https://mysteriousuniverse.org/?p=167650")
        EpisodeFactory(podcast=podcast, guid="https://mysteriousuniverse.org/?p=167326")

        # check episode not present is deleted
        EpisodeFactory(podcast=podcast, guid="some-random")

        self.assertEqual(len(podcast.sync_rss_feed()), 17)
        podcast.refresh_from_db()

        self.assertEqual(podcast.episode_set.count(), 20)
        self.assertFalse(Episode.objects.filter(guid="some-random").exists())
