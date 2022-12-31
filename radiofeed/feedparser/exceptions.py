from __future__ import annotations


class FeedParserError(ValueError):
    """Base feed parser exception."""


class InvalidRSS(FeedParserError):
    """Error parsing RSS content."""


class NotModified(FeedParserError):
    """RSS feed has not been modified since last update."""


class Duplicate(FeedParserError):
    """Another identical podcast exists in the database."""


class Unavailable(FeedParserError):
    """Content is inaccessible due to temporary network issue, 500 error etc."""


class Inaccessible(FeedParserError):
    """Content is forbidden, no longer exists or other server issue."""
