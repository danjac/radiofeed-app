from radiofeed import iterators


class TestBatcher:
    def test_batcher(self):
        batches = list(iterators.batcher(range(100), batch_size=10))
        assert len(batches) == 10
        assert batches[0] == list(range(10))
