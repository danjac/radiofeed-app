from radiofeed.podcasts.models import Podcast


class FeedParserError(ValueError):
    """Base feed parser exception."""

    parser_error: str = ""


class Duplicate(FeedParserError):
    """Another identical podcast exists in the database."""

    parser_error: str = Podcast.ParserError.DUPLICATE  # type: ignore


class Inaccessible(FeedParserError):
    """Content is forbidden, no longer exists or other server issue."""

    parser_error: str = Podcast.ParserError.INACCESSIBLE  # type: ignore


class InvalidRSS(FeedParserError):
    """Error parsing RSS content."""

    parser_error: str = Podcast.ParserError.INVALID_RSS  # type: ignore


class NotModified(FeedParserError):
    """RSS feed has not been modified since last update."""

    parser_error: str = Podcast.ParserError.NOT_MODIFIED  # type: ignore


class Unavailable(FeedParserError):
    """Content is inaccessible due to temporary network issue, 500 error etc."""

    parser_error: str = Podcast.ParserError.UNAVAILABLE  # type: ignore
