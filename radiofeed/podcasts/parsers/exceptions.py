import httpx

from radiofeed.podcasts.models import Podcast


class FeedParserError(Exception):
    """Base feed parser exception."""

    status: Podcast.FeedStatus | None = None

    def __init__(self, *args, response: httpx.Response | None = None, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)


class TransientFeedParserError(FeedParserError):
    """Error which may be resolved by retrying later."""


class PermanentFeedParserError(FeedParserError):
    """Error which is unlikely to be resolved by retrying later."""


class DuplicateError(PermanentFeedParserError):
    """Another identical podcast exists in the database."""

    status = Podcast.FeedStatus.DUPLICATE

    def __init__(self, *args, canonical_id: int | None = None, **kwargs):
        self.canonical_id = canonical_id
        super().__init__(*args, **kwargs)


class DiscontinuedError(PermanentFeedParserError):
    """Podcast has been marked discontinued and no longer available."""

    status = Podcast.FeedStatus.DISCONTINUED


class InvalidRSSError(PermanentFeedParserError):
    """Error parsing RSS content."""

    status = Podcast.FeedStatus.INVALID_RSS


class PermanentHTTPError(PermanentFeedParserError):
    """Content is inaccessible due to permanent HTTP issue e.g. not found"""

    status = Podcast.FeedStatus.PERMANENT_HTTP_ERROR


class TransientHTTPError(TransientFeedParserError):
    """Content is inaccessible due to temporary HTTP issue e.g. server error"""

    status = Podcast.FeedStatus.TRANSIENT_HTTP_ERROR


class NetworkError(TransientFeedParserError):
    """Content is inaccessible due to network issue."""

    status = Podcast.FeedStatus.NETWORK_ERROR


class DatabaseOperationError(TransientFeedParserError):
    """Error caused by failed database update."""

    status = Podcast.FeedStatus.DATABASE_ERROR


class NotModifiedError(TransientFeedParserError):
    """RSS feed has not been modified since last update."""

    status = Podcast.FeedStatus.NOT_MODIFIED
