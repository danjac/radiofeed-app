import httpx

from listenwave.podcasts.models import Podcast


class FeedParserError(Exception):
    """Base feed parser exception."""

    result: Podcast.ParserResult

    def __init__(self, *args, response: httpx.Response | None = None, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)


class DatabaseError(FeedParserError):
    """Error caused by failed database update."""

    result = Podcast.ParserResult.DATABASE_ERROR


class NotModifiedError(FeedParserError):
    """RSS feed has not been modified since last update."""

    result = Podcast.ParserResult.NOT_MODIFIED


class TransientNetworkError(FeedParserError):
    """Content is inaccessible due to temporary network issue, 500 error etc."""

    result = Podcast.ParserResult.TEMPORARY_NETWORK_ERROR


class DiscontinuedError(FeedParserError):
    """Podcast has been discontinued and no longer available."""

    result = Podcast.ParserResult.DISCONTINUED


class DuplicateError(FeedParserError):
    """Another identical podcast exists in the database."""

    result = Podcast.ParserResult.DUPLICATE

    def __init__(self, *args, canonical_id: int | None = None, **kwargs):
        self.canonical_id = canonical_id
        super().__init__(*args, **kwargs)


class InvalidRSSError(FeedParserError):
    """Error parsing RSS content."""

    result = Podcast.ParserResult.INVALID_RSS


class PermanentNetworkError(FeedParserError):
    """Content is inaccessible due to temporary network issue, 500 error etc."""

    result = Podcast.ParserResult.PERMANENT_NETWORK_ERROR
