import json

from datetime import timedelta

from django.utils import timezone

from jcasts.podcasts import podping
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast


class TestGetUpdates:
    def test_batch(self, db, mocker, mock_feed_queue, faker):

        urls = [faker.url() for _ in range(33)]

        for url in urls[:3]:
            PodcastFactory(rss=url)

        mocker.patch("jcasts.podcasts.podping.get_stream", return_value=iter(urls))

        urls = list(podping.get_updates(timedelta(minutes=15)))

        assert len(urls) == 3
        assert len(mock_feed_queue.enqueued) == 3

        assert Podcast.objects.filter(podping=True, queued__isnull=False).count() == 3


class TestGetStream:
    def test_stream(self, mocker):

        posts = [
            {
                "id": "podping",
                "required_posting_auths": [1],
                "json": json.dumps(
                    {
                        "url": "https://example.com/",
                    }
                ),
            },
        ]

        class MockAccount:
            def __init__(self, **kwargs):
                pass

            def get_following(self):
                return [1, 2, 3]

        class MockBlockchain:
            def __init__(self, **kwargs):
                pass

            def get_estimated_block_num(self, dt):
                return 1

            def stream(self, *ags, **kwargs):
                return iter(posts)

        mocker.patch(
            "jcasts.podcasts.podping.Blockchain", return_value=MockBlockchain()
        )
        mocker.patch("jcasts.podcasts.podping.Account", return_value=MockAccount())

        urls = list(podping.get_stream(timedelta(minutes=15)))
        assert len(urls) == 1
        assert urls[0] == "https://example.com/"


class TestParseUrls:
    def test_parse_single_url(self):
        data = json.dumps(
            {
                "url": "https://example.com",
            }
        )
        urls = list(podping.parse_urls(data))
        assert len(urls) == 1
        assert urls[0] == "https://example.com"

    def test_parse_multiple_urls(self):
        data = json.dumps(
            {
                "urls": [
                    "https://example1.com",
                    "https://example2.com",
                    "https://example3.com",
                ]
            }
        )
        urls = list(podping.parse_urls(data))
        assert len(urls) == 3
        assert urls[0] == "https://example1.com"
        assert urls[1] == "https://example2.com"
        assert urls[2] == "https://example3.com"


class TestBatchUpdates:
    def test_no_podcasts(self, db, mock_feed_queue, faker):
        now = timezone.now()

        # queued
        queued = PodcastFactory(queued=now)

        # recently updated
        recent = PodcastFactory(parsed=now - timedelta(minutes=5))

        urls = [recent.rss, queued.rss] + [faker.url for _ in range(12)]

        feeds = list(podping.batch_updates(timedelta(minutes=15), set(urls)))

        assert len(feeds) == 0
        assert len(mock_feed_queue.enqueued) == 0

        qs = Podcast.objects.filter(podping=True, queued__isnull=False)

        assert qs.count() == 0

    def test_update(self, db, mock_feed_queue, faker):

        now = timezone.now()

        # queued
        queued = PodcastFactory(queued=now)

        # recently updated
        recent = PodcastFactory(parsed=now - timedelta(minutes=5))

        # for update
        podcasts = PodcastFactory.create_batch(3)
        podcast_urls = [p.rss for p in podcasts]

        urls = podcast_urls + [recent.rss, queued.rss] + [faker.url for _ in range(12)]

        feeds = list(podping.batch_updates(timedelta(minutes=15), set(urls)))

        assert set(feeds) == set(podcast_urls), feeds

        assert len(mock_feed_queue.enqueued) == 3

        qs = Podcast.objects.filter(podping=True, queued__isnull=False)

        assert qs.count() == 3
        assert queued not in qs
        assert recent not in qs
