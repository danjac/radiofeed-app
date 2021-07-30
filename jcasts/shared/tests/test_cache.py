from jcasts.shared.cache import make_cache_key, make_key_prefix


class TestMakeCacheKey:
    def test_make_key(self):
        key = make_cache_key("page-1", "", 1)
        assert make_cache_key("page-1", "", 1) == key
        make_key_prefix.cache_clear()
        assert make_cache_key("page-1", "", 1) != key
