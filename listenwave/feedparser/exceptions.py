import httpx

from listenwave.podcasts.models import Podcast


class FeedParserError(Exception):
    """Base feed parser exception."""

    result: Podcast.ParserResult

    def __init__(self, *args, response: httpx.Response | None = None, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)


class DiscontinuedError(FeedParserError):
    """Podcast has been discontinued and no longer available."""

    result = Podcast.ParserResult.DISCONTINUED


class DuplicateError(FeedParserError):
    """Another identical podcast exists in the database."""

    result = Podcast.ParserResult.DUPLICATE


class InvalidRSSError(FeedParserError):
    """Error parsing RSS content."""

    result = Podcast.ParserResult.INVALID_RSS


class NotModifiedError(FeedParserError):
    """RSS feed has not been modified since last update."""

    result = Podcast.ParserResult.NOT_MODIFIED


class UnavailableError(FeedParserError):
    """Content is inaccessible due to temporary network issue, 500 error etc."""

    result = Podcast.ParserResult.UNAVAILABLE


class InvalidDataError(FeedParserError):
    """Error caused by invalid data e.g. bad date strings."""

    result = Podcast.ParserResult.INVALID_DATA
