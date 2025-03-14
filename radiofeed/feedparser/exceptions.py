import httpx

from radiofeed.podcasts.models import Podcast


class FeedParserError(Exception):
    """Base feed parser exception."""

    parser_error: Podcast.ParserError

    def __init__(self, *args, response: httpx.Response | None = None, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)


class DiscontinuedError(FeedParserError):
    """Podcast has been discontinued and no longer available."""

    parser_error = Podcast.ParserError.DISCONTINUED


class DuplicateError(FeedParserError):
    """Another identical podcast exists in the database."""

    parser_error = Podcast.ParserError.DUPLICATE


class InvalidRSSError(FeedParserError):
    """Error parsing RSS content."""

    parser_error = Podcast.ParserError.INVALID_RSS


class NotModifiedError(FeedParserError):
    """RSS feed has not been modified since last update."""

    parser_error = Podcast.ParserError.NOT_MODIFIED


class UnavailableError(FeedParserError):
    """Content is inaccessible due to temporary network issue, 500 error etc."""

    parser_error = Podcast.ParserError.UNAVAILABLE


class InvalidDataError(FeedParserError):
    """Error caused by invalid data e.g. bad date strings."""

    parser_error = Podcast.ParserError.INVALID_DATA
