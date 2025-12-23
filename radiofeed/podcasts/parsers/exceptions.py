from radiofeed.podcasts.models import Podcast


class FeedParseError(Exception):
    """Error parsing the podcast feed."""

    feed_status: str | None = None


class DuplicateError(FeedParseError):
    """Another identical podcast exists in the database."""

    feed_status = Podcast.FeedStatus.DUPLICATE

    def __init__(self, *args, canonical_id: int | None = None, **kwargs):
        self.canonical_id = canonical_id
        super().__init__(*args, **kwargs)


class DiscontinuedError(FeedParseError):
    """Podcast has been marked discontinued and no longer available."""

    feed_status = Podcast.FeedStatus.DISCONTINUED


class NotModifiedError(FeedParseError):
    """RSS feed has not been modified since last update."""

    feed_status = Podcast.FeedStatus.NOT_MODIFIED


class InvalidRSSError(FeedParseError):
    """The RSS or Atom feed is invalid or unparseable."""

    feed_status = Podcast.FeedStatus.INVALID_RSS


class UnavailableError(FeedParseError):
    """The podcast feed is temporarily unavailable (e.g., HTTP 503)."""

    feed_status = Podcast.FeedStatus.UNAVAILABLE
