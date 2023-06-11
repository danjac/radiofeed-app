from radiofeed.podcasts.models import Podcast


class FeedParserError(ValueError):
    """Base feed parser exception."""

    parser_error: tuple[str, str] | None = None


class DuplicateError(FeedParserError):
    """Another identical podcast exists in the database."""

    parser_error = Podcast.ParserError.DUPLICATE


class InaccessibleError(FeedParserError):
    """Content is forbidden, no longer exists or other server issue."""

    parser_error = Podcast.ParserError.INACCESSIBLE


class InvalidRSSError(FeedParserError):
    """Error parsing RSS content."""

    parser_error = Podcast.ParserError.INVALID_RSS


class NotModifiedError(FeedParserError):
    """RSS feed has not been modified since last update."""

    parser_error = Podcast.ParserError.NOT_MODIFIED


class UnavailableError(FeedParserError):
    """Content is inaccessible due to temporary network issue, 500 error etc."""

    parser_error = Podcast.ParserError.UNAVAILABLE
