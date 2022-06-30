import itertools
import secrets

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]


def get_user_agent():
    """
    Returns randomly selected HTTP header User Agent

    Returns:
        str: user agent
    """
    return secrets.choice(USER_AGENTS)


def batcher(iterable, batch_size):
    """
    Batches an iterable into lists of given batch size. Useful for handling long
    iterables where individual processing might be slow.

    Args:
        iterable (Iterable): any iterable object
        batch_size (int): maximum size of each batch

    Yields:
        list: a list containing individual items in each batch
    """
    iterator = iter(iterable)
    while batch := list(itertools.islice(iterator, batch_size)):
        yield batch
