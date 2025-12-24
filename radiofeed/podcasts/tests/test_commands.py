import pytest
from django.core.management import CommandError, call_command

from radiofeed.podcasts.itunes import Feed, ItunesError
from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from radiofeed.users.tests.factories import EmailAddressFactory


class TestParsePodcastFeeds:
    parse_feed = "radiofeed.podcasts.management.commands.parse_podcast_feeds.parse_feed"

    @pytest.fixture
    def mock_parse(self, mocker):
        return mocker.patch(self.parse_feed)

    @pytest.mark.django_db
    def test_ok(self, mocker):
        mock_parse = mocker.patch(self.parse_feed)
        PodcastFactory(pub_date=None)
        call_command("parse_podcast_feeds")
        mock_parse.assert_called()

    @pytest.mark.django_db
    def test_not_scheduled(self, mocker):
        mock_parse = mocker.patch(self.parse_feed)
        PodcastFactory(active=False)
        call_command("parse_podcast_feeds")
        mock_parse.assert_not_called()


class TestFetchItunesFeeds:
    mock_fetch = "radiofeed.podcasts.management.commands.fetch_itunes_feeds.itunes.fetch_top_feeds"
    mock_save = "radiofeed.podcasts.management.commands.fetch_itunes_feeds.itunes.save_feeds_to_db"

    @pytest.fixture
    def category(self):
        return CategoryFactory(itunes_genre_id=1301)

    @pytest.fixture
    def feed(self):
        return Feed(
            artworkUrl100="https://example.com/test.jpg",
            collectionName="example",
            collectionViewUrl="https://example.com/",
            feedUrl="https://example.com/rss/",
        )

    @pytest.mark.django_db
    def test_ok(self, category, mocker, feed):
        mock_fetch = mocker.patch(self.mock_fetch, return_value=[feed])
        mock_save_feeds = mocker.patch(self.mock_save)
        call_command("fetch_itunes_feeds", min_jitter=0, max_jitter=0)
        mock_fetch.assert_called()
        mock_save_feeds.assert_any_call([feed], promoted=True)
        mock_save_feeds.assert_any_call([feed])

    @pytest.mark.django_db
    def test_invalid_country_codes(self):
        with pytest.raises(CommandError):
            call_command(
                "fetch_itunes_feeds", min_jitter=0, max_jitter=0, countries=["us", "tx"]
            )

    @pytest.mark.django_db
    def test_no_chart_feeds(self, category, mocker, feed):
        mock_fetch = mocker.patch(self.mock_fetch, return_value=[])
        mock_save_feeds = mocker.patch(self.mock_save)
        call_command("fetch_itunes_feeds", min_jitter=0, max_jitter=0)
        mock_fetch.assert_called()
        mock_save_feeds.assert_not_called()

    @pytest.mark.django_db
    def test_itunes_error(self, mocker):
        mock_fetch = mocker.patch(
            self.mock_fetch, side_effect=ItunesError("Error fetching iTunes")
        )
        mock_save_feeds = mocker.patch(self.mock_save)
        call_command("fetch_itunes_feeds", min_jitter=0, max_jitter=0)
        mock_fetch.assert_called()
        mock_save_feeds.assert_not_called()


class TestCreatePodcastRecommendations:
    @pytest.mark.django_db
    def test_create_recommendations(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=RecommendationFactory.create_batch(3),
        )
        call_command("create_podcast_recommendations")
        patched.assert_called()


class TestSendPodcastRecommendations:
    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(verified=True, primary=True)

    @pytest.mark.django_db(transaction=True)
    def test_ok(self, recipient, mailoutbox):
        podcast = SubscriptionFactory(subscriber=recipient.user).podcast
        RecommendationFactory(podcast=podcast)
        call_command("send_podcast_recommendations")
        assert len(mailoutbox) == 1

    @pytest.mark.django_db(transaction=True)
    def test_no_recommendations(self, recipient, mailoutbox):
        PodcastFactory()
        call_command("send_podcast_recommendations")
        assert len(mailoutbox) == 0
