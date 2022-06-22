from __future__ import annotations

import itertools

from typing import Generator, Iterable


def batcher(iterable: Iterable, batch_size: int) -> Generator[list, None, None]:
    iterator = iter(iterable)
    while batch := list(itertools.islice(iterator, batch_size)):
        yield batch
