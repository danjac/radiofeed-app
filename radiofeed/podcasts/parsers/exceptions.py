import httpx

from radiofeed.podcasts.models import Podcast


class FeedParserError(Exception):
    """Base feed parser exception."""

    status: Podcast.FeedStatus | None = None


class DuplicateError(FeedParserError):
    """Another identical podcast exists in the database."""

    status = Podcast.FeedStatus.DUPLICATE

    def __init__(self, *args, canonical_id: int | None = None, **kwargs):
        self.canonical_id = canonical_id
        super().__init__(*args, **kwargs)


class DatabaseError(FeedParserError):
    """Error caused by failed database update."""

    status = Podcast.FeedStatus.DATABASE_ERROR


class DiscontinuedError(FeedParserError):
    """Podcast has been marked discontinued and no longer available."""

    status = Podcast.FeedStatus.DISCONTINUED


class InvalidRSSError(FeedParserError):
    """Error parsing RSS content."""

    status = Podcast.FeedStatus.INVALID_RSS


class NetworkError(FeedParserError):
    """Content is inaccessible due to permanent HTTP issue e.g. not found"""

    status = Podcast.FeedStatus.NETWORK_ERROR


class NotModifiedError(FeedParserError):
    """RSS feed has not been modified since last update."""

    status = Podcast.FeedStatus.NOT_MODIFIED

    def __init__(self, *args, response: httpx.Response | None = None, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)
