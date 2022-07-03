import requests


class NotModified(requests.RequestException):
    """RSS feed has not been modified since last update."""


class DuplicateFeed(requests.RequestException):
    """Another identical podcast exists in the database."""


class RssParserError(ValueError):
    """Broken XML syntax or missing/invalid required attributes."""
