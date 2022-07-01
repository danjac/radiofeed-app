from radiofeed.podcasts.feed_parser.feed_parser import FeedParser


def parse_feed(podcast):
    """Updates a Podcast instance with its RSS or Atom feed source.

    Args:
        podcast (Podcast)

    Returns:
        bool: if successful update
    """
    return FeedParser(podcast).parse()
