from __future__ import annotations

from radiofeed import iterators


class TestChunkedIterator:
    def test_chunked_iterator(self):
        batches = list(iterators.chunked_iterator(range(100), batch_size=10))
        assert len(batches) == 10
        assert batches[0] == list(range(10))
