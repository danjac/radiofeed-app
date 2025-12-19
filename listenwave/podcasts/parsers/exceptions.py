import httpx


class FeedParserError(Exception):
    """Base feed parser exception."""

    def __init__(self, *args, response: httpx.Response | None = None, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)


class DuplicateError(FeedParserError):
    """Another identical podcast exists in the database."""

    def __init__(self, *args, canonical_id: int | None = None, **kwargs):
        self.canonical_id = canonical_id
        super().__init__(*args, **kwargs)


class DatabaseOperationError(FeedParserError):
    """Error caused by failed database update."""


class NotModifiedError(FeedParserError):
    """RSS feed has not been modified since last update."""


class TransientNetworkError(FeedParserError):
    """Content is inaccessible due to temporary network issue, 500 error etc."""


class DiscontinuedError(FeedParserError):
    """Podcast has been discontinued and no longer available."""


class InvalidRSSError(FeedParserError):
    """Error parsing RSS content."""


class PermanentNetworkError(FeedParserError):
    """Content is inaccessible due to temporary network issue, 500 error etc."""
