import itertools

from typing import Generator, Iterable


def batcher(iterable: Iterable, batch_size: int) -> Generator[list, None, None]:
    """Batches an iterable into lists of given batch size.

    Useful for handling long iterables where individual processing might be slow.
    """
    iterator = iter(iterable)
    while batch := list(itertools.islice(iterator, batch_size)):
        yield batch
