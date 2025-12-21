class FeedParseError(Exception):
    """Error parsing the podcast feed."""


class DuplicateError(Exception):
    """Another identical podcast exists in the database."""

    def __init__(self, *args, canonical_id: int | None = None, **kwargs):
        self.canonical_id = canonical_id
        super().__init__(*args, **kwargs)


class DiscontinuedError(FeedParseError):
    """Podcast has been marked discontinued and no longer available."""


class NotModifiedError(FeedParseError):
    """RSS feed has not been modified since last update."""


class InvalidRSSError(Exception):
    """The RSS or Atom feed is invalid or unparseable."""
