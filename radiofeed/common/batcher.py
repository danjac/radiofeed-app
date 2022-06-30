import itertools


def batcher(iterable, batch_size):
    """Batches an iterable into lists of given batch size. Useful for handling long
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
