import requests


class NotModified(requests.RequestException):
    ...


class DuplicateFeed(requests.RequestException):
    ...


class RssParserError(ValueError):
    ...
