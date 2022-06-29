import itertools


def batcher(iterable, batch_size):
    iterator = iter(iterable)
    while batch := list(itertools.islice(iterator, batch_size)):
        yield batch
