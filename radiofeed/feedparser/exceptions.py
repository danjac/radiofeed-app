from radiofeed.podcasts.models import Podcast


class FeedParserError(ValueError):
    """Base feed parser exception."""

    parser_error: tuple[str, str] | None = None


class Duplicate(FeedParserError):
    """Another identical podcast exists in the database."""

    parser_error = Podcast.ParserError.DUPLICATE


class Inaccessible(FeedParserError):
    """Content is forbidden, no longer exists or other server issue."""

    parser_error = Podcast.ParserError.INACCESSIBLE


class InvalidRSS(FeedParserError):
    """Error parsing RSS content."""

    parser_error = Podcast.ParserError.INVALID_RSS


class NotModified(FeedParserError):
    """RSS feed has not been modified since last update."""

    parser_error = Podcast.ParserError.NOT_MODIFIED


class Unavailable(FeedParserError):
    """Content is inaccessible due to temporary network issue, 500 error etc."""

    parser_error = Podcast.ParserError.UNAVAILABLE
