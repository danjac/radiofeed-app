class FeedParserError(Exception):
    """Base feed parser exception."""


class DuplicateError(FeedParserError):
    """Another identical podcast exists in the database."""

    def __init__(self, *args, canonical_id: int | None = None, **kwargs):
        self.canonical_id = canonical_id
        super().__init__(*args, **kwargs)


class DatabaseError(FeedParserError):
    """Error caused by failed database update."""


class DiscontinuedError(FeedParserError):
    """Podcast has been marked discontinued and no longer available."""


class InvalidRSSError(FeedParserError):
    """Error parsing RSS content."""


class NetworkError(FeedParserError):
    """Content is inaccessible due to permanent HTTP issue e.g. not found"""


class NotModifiedError(FeedParserError):
    """RSS feed has not been modified since last update."""
